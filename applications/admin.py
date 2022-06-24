from flask import Flask, request, jsonify
from configuration import Configuration
from models import database, Product, ProductOrder, Category, ProductCategory
from flask_jwt_extended import JWTManager, jwt_required, get_jwt
from sqlalchemy import desc, func, asc

application = Flask(__name__)
application.config.from_object(Configuration)
jwt = JWTManager(application)

@application.route("/productStatistics", methods=["GET"])
@jwt_required()
def productStatistics():
    claims = get_jwt()

    if ("role" not in claims) or ("admin" != claims["role"]):
        return jsonify(msg="Missing Authorization Header"), 401

    productsFromOrders = ProductOrder.query.all()
    statistics = {}
    for productOrder in productsFromOrders:
        product = Product.query.filter(Product.id == productOrder.productId).first()
        if product.name not in statistics:
            statistics[product.name] = (productOrder.requested, productOrder.requested - productOrder.received)
        else:
            statistics[product.name] = (int(statistics[product.name][0]) + productOrder.requested,
                                int(statistics[product.name][1]) + (productOrder.requested - productOrder.received))

    statisticsJSON = []
    for productName in statistics.keys():
        productJSON = {
            "name": productName,
            "sold": statistics[productName][0],
            "waiting": statistics[productName][1]
        }
        statisticsJSON.append(productJSON)

    return jsonify(statistics=statisticsJSON), 200


@application.route("/categoryStatistics", methods=["GET"])
@jwt_required()
def categoryStatistics():
    claims = get_jwt()

    if ("role" not in claims) or ("admin" != claims["role"]):
        return jsonify(msg="Missing Authorization Header"), 401

    categories = database.session.query(Category.name, Category.id, func.count(Category.id)).join(ProductCategory, isouter=True).\
                    join(ProductOrder, ProductCategory.productId == ProductOrder.productId, isouter=True).\
                    group_by(Category.id).order_by(desc(func.sum(ProductOrder.requested)), asc(Category.name)).all()

    categoriesOutput = [category.name for category in categories]

    print(categories, flush=True)
    return jsonify(statistics=categoriesOutput), 200

@application.route("/clear", methods=["GET", "POST"])
def clear_all():
    meta = database.metadata
    engine = database.engine
    con = engine.connect()
    trans = con.begin()
    con.execute('SET FOREIGN_KEY_CHECKS = 0;')
    for table in meta.sorted_tables:
        con.execute(table.delete())
    con.execute('SET FOREIGN_KEY_CHECKS = 1;')
    con.execute('ALTER TABLE products AUTO_INCREMENT=1;')
    con.execute('ALTER TABLE orders AUTO_INCREMENT=1;')
    con.execute('ALTER TABLE categories AUTO_INCREMENT=1;')
    trans.commit()

    return str(Product.query.all())


if __name__ == "__main__":
    database.init_app(application)
    application.run(debug=True, host="0.0.0.0", port=5003)
