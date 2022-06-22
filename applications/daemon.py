from flask import Flask
from configuration import Configuration
from redis import Redis
from models import database, Product, Category, Order, ProductCategory, ProductOrder
from sqlalchemy import and_

application = Flask(__name__)
application.config.from_object(Configuration)

if __name__ == "__main__":
    print("Daemon started", flush=True)
    database.init_app(application)

    with application.app_context():
        with Redis(host=Configuration.REDIS_HOST, port=6379) as redis:
            while True:
                updatedProducts = redis.blpop(Configuration.REDIS_PRODUCT_LIST)[1]
                products = updatedProducts.decode("utf-8")
                productParsed = products.split(";")

                # print(productParsed, flush=True)

                database.session.expire_all()
                database.session.commit()

                existingProduct = Product.query.filter(Product.name == productParsed[1]).first()
                if existingProduct is None:
                    newProduct = Product(
                        name=productParsed[1],
                        quantity=int(productParsed[2]),
                        price=float(productParsed[3])
                    )
                    database.session.add(newProduct)
                    database.session.commit()

                    categories = productParsed[0].split("|")
                    for categoryName in categories:
                        category = Category.query.filter(Category.name == categoryName).first()
                        if category is None:
                            category = Category(name=categoryName)
                            database.session.add(category)
                            database.session.commit()

                        productCategory = ProductCategory(
                            productId=newProduct.id,
                            categoryId=category.id
                        )
                        database.session.add(productCategory)
                        database.session.commit()
                else:
                    categories = productParsed[0].split("|")
                    categoriesProduct = existingProduct.categories
                    for category in categories:
                        found = False
                        for categoryProduct in categoriesProduct:
                            if category == categoryProduct.name:
                                found = True
                                break
                        if not found:
                            break
                    if found is True:
                        newPrice = (existingProduct.quantity * existingProduct.price +
                                    int(productParsed[2]) * float(productParsed[3])) / (existingProduct.quantity + int(productParsed[2]))
                        existingProduct.price = newPrice
                        existingProduct.quantity += int(productParsed[2])
                        # print("Postoji proizvod: " + existingProduct.name + ", kol: " + str(existingProduct.quantity) + ", cena" + str(existingProduct.price),
                             # flush=True)
                        database.session.commit()

                database.session.expire_all()
                database.session.commit()

                orders = Order.query.filter(Order.status == "PENDING").all()
                for order in orders:
                    products = order.products
                    for product in products:
                        productOrder = ProductOrder.query.filter(
                            and_(
                                ProductOrder.productId == product.id,
                                ProductOrder.orderId == order.id
                            )
                        ).first()
                        print(productOrder, flush=True)
                        if productOrder is not None:
                            productsToSend = min(productOrder.requested - productOrder.received, product.quantity)
                            product.quantity -= productsToSend
                            productOrder.received += productsToSend
                    database.session.commit()

                    hasEverything = True
                    for product in products:
                        productOrder = ProductOrder.query.filter(
                            and_(
                                ProductOrder.productId == product.id,
                                ProductOrder.orderId == order.id
                            )
                        ).first()
                        if productOrder.requested != productOrder.received:
                            hasEverything = False
                            break
                    if hasEverything:
                        order.status = "COMPLETE"
                        database.session.commit()

