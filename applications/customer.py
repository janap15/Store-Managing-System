from flask import Flask, request, jsonify
from configuration import Configuration
from models import database, Product, Category, Order, ProductOrder
from flask_jwt_extended import JWTManager, jwt_required, get_jwt
from datetime import datetime
from sqlalchemy import and_

application = Flask(__name__)
application.config.from_object(Configuration)
jwt = JWTManager(application)


@application.route("/search", methods=["GET"])
@jwt_required()
def search():
    claims = get_jwt()

    if ("role" not in claims) or ("customer" != claims["role"]):
        return jsonify(msg="Missing Authorization Header"), 401

    args = request.args
    name = args.get("name", default=None)
    category = args.get("category", default=None)

    categoriesList = []
    productsList = []

    if name is None and category is None:
        categories = Category.query.all()
        for category in categories:
            categoriesList.append(category.name)

        products = Product.query.all()
        for product in products:
            categoriesProduct = product.categories
            categoriesForJSON = []
            for cat in categoriesProduct:
                categoriesForJSON.append(cat.name)
            productJSON = {
                "categories": categoriesForJSON,
                "id": product.id,
                "name": product.name,
                "price": product.price,
                "quantity": product.quantity
            }
            productsList.append(productJSON)

        return jsonify(categories=categoriesList, products=productsList), 200

    elif name is not None and category is None:
        products = Product.query.filter(Product.name.like(f"%{name}%")).all()
        for product in products:
            categoriesProduct = product.categories
            categoriesForJSON = []
            for category in categoriesProduct:
                categoriesForJSON.append(category.name)
                found = False
                for cat in categoriesList:
                    if cat == category.name:
                        found = True
                        break
                if found is False:
                    categoriesList.append(category.name)
            productJSON = {
                "categories": categoriesForJSON,
                "id": product.id,
                "name": product.name,
                "price": product.price,
                "quantity": product.quantity
            }
            productsList.append(productJSON)

        return jsonify(categories=categoriesList, products=productsList), 200

    elif name is None and category is not None:
        categories = Category.query.filter(Category.name.like(f"%{category}%")).all()
        for category in categories:
            categoriesList.append(category.name)

        products = Product.query.all()
        for product in products:
            categoriesProduct = product.categories
            categoriesForJSON = []
            found = False
            for category in categoriesList:
                for cat in categoriesProduct:
                    if cat.name == category:
                        found = True
            if found is True:
                for cat in categoriesProduct:
                    categoriesForJSON.append(cat.name)
                productJSON = {
                    "categories": categoriesForJSON,
                    "id": product.id,
                    "name": product.name,
                    "price": product.price,
                    "quantity": product.quantity
                }
                productsList.append(productJSON)

        return jsonify(categories=categoriesList, products=productsList), 200

    elif name is not None and category is not None:
        categories = Category.query.filter(Category.name.like(f"%{category}%")).all()
        products = Product.query.filter(Product.name.like(f"%{name}%")).all()

        categoriesList = []
        productsList = []

        for category in categories:
            found = False
            for product in products:
                categoriesProduct = product.categories
                for cat in categoriesProduct:
                    if cat.name == category:
                        found = True
                        break
            if found:
                categoriesList.append(category)

        for product in products:
            found = False
            categoriesProduct = product.categories
            for category in categories:
                for cat in categoriesProduct:
                    if cat.name == category:
                        found = True
                        break
            if found:
                productsList.append(product)

        productListForResult = []
        for product in productsList:
            categoriesProduct = product.categories
            categoriesForJSON = []
            for cat in categoriesProduct:
                categoriesForJSON.append(cat.name)
            productJSON = {
                "categories": categoriesForJSON,
                "id": product.id,
                "name": product.name,
                "price": product.price,
                "quantity": product.quantity
            }
            productListForResult.append(productJSON)

        return jsonify(categories=categoriesList, products=productListForResult), 200


@application.route("/order", methods=["POST"])
@jwt_required()
def order():
    claims = get_jwt()
    customerEmail = claims["email"]

    if ("role" not in claims) or ("customer" != claims["role"]):
        return jsonify(msg="Missing Authorization Header"), 401

    requests = request.json.get("requests", None)
    if requests is None:
        return jsonify(message="Field requests is missing."), 400

    price = 0
    for i in range(len(requests)):
        product = requests[i]

        try:
            id = product["id"]
        except KeyError:
            id = None
        if id is None:
            return jsonify(message=f"Product id is missing for request number {i}."), 400

        try:
            quantity = product["quantity"]
        except KeyError:
            quantity = None
        if quantity is None:
            return jsonify(message=f"Product quantity is missing for request number {i}."), 400

        isInt = True
        try:
            int(id)
        except ValueError:
            isInt = False
        if not isInt or id < 0:
            return jsonify(message=f"Invalid product id for request number {i}."), 400

        try:
            int(quantity)
        except ValueError:
            isInt = False
        if not isInt or quantity < 0:
            return jsonify(message=f"Invalid product quantity for request number {i}."), 400

        productExists = Product.query.filter(Product.id == id).first()
        if productExists is None:
            return jsonify(message=f"Invalid product for request number {i}."), 400

        price += (productExists.price * quantity)

    order = Order(
        price=price,
        status="PENDING",
        timestamp=datetime.utcnow(),
        customerEmail=customerEmail
    )
    database.session.add(order)
    database.session.commit()

    isCompleted = True
    for i in range(len(requests)):
        product = requests[i]
        id = int(product["id"])
        quantity = int(product["quantity"])
        product = Product.query.filter(Product.id == id).first()
        if product.quantity < quantity:
            isCompleted = False

    for i in range(len(requests)):
        requestedProduct = requests[i]
        id = int(requestedProduct["id"])
        quantity = int(requestedProduct["quantity"])

        product = Product.query.filter(Product.id == id).first()

        received = min(quantity, product.quantity)
        product.quantity -= received

        productOrder = ProductOrder(
            productId=id,
            orderId=order.id,
            requested=quantity,
            received=received,
            productPrice=product.price
        )
        database.session.add(productOrder)
        database.session.commit()

    if isCompleted:
        order.status = "COMPLETE"
        database.session.commit()

    return jsonify(id=order.id), 200


@application.route("/status", methods=["GET"])
@jwt_required()
def status():
    claims = get_jwt()
    customerEmail = claims["email"]

    if ("role" not in claims) or ("customer" != claims["role"]):
        return jsonify(msg="Missing Authorization Header"), 401

    orders = Order.query.filter(Order.customerEmail == customerEmail).all()
    ordersList = []
    for order in orders:
        products = order.products
        productsJSON = []
        for product in products:
            categories = product.categories
            categoriesNames = []
            for category in categories:
                categoriesNames.append(category.name)
            productOrder = ProductOrder.query.filter(
                and_(
                    ProductOrder.productId == product.id,
                    ProductOrder.orderId == order.id
                )
            ).first()
            productJSON = {
                "categories": categoriesNames,
                "name": product.name,
                "price": productOrder.productPrice,
                "received": productOrder.received,
                "requested": productOrder.requested
            }
            productsJSON.append(productJSON)
        ordersList.append({
            "products": productsJSON,
            "price": order.price,
            "status": order.status,
            "timestamp": order.timestamp.strftime("%Y-%m-%dT%H:%M:%SZ")
        })

    return jsonify(orders=ordersList), 200


if __name__ == "__main__":
    database.init_app(application)
    application.run(debug=True, host="0.0.0.0", port=5001)
