from flask import Flask, request, Response, jsonify
from configuration import Configuration
from models import database, Product
from flask_jwt_extended import JWTManager, jwt_required, get_jwt
from redis import Redis
import io
import csv

application = Flask(__name__)
application.config.from_object(Configuration)
jwt = JWTManager(application)

@application.route("/update", methods=["POST"])
@jwt_required()
def update():
    claims = get_jwt()

    if ("role" not in claims) or ("manager" != claims["role"]):
        return jsonify(msg="Missing Authorization Header"), 401

    if request.files.get("file", None) is None:
        return jsonify(message="Field file is missing."), 400

    content = request.files["file"].stream.read().decode("utf-8")
    stream = io.StringIO(content)
    reader = csv.reader(stream)

    products = []
    line = 0
    for row in reader:
        if len(row) != 4:
            return jsonify(message=f"Incorrect number of values on line {line}."), 400

        if not row[2].isdigit() or int(row[2]) < 0:
            return jsonify(message=f"Incorrect quantity on line {line}."), 400

        isFloat = True
        try:
            float(row[3])
        except ValueError:
            isFloat = False

        if not isFloat or float(row[3]) < 0:
            return jsonify(message=f"Incorrect price on line {line}."), 400

        products.append(row[0] + ";" + row[1] + ";" + row[2] + ";" + row[3])
        line += 1

    with Redis(host=Configuration.REDIS_HOST, port=6379) as redis:
        for product in products:
            print(product, flush=True)
            redis.rpush(Configuration.REDIS_PRODUCT_LIST, product)

    return Response(status=200)

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
    application.run(debug=True, host="0.0.0.0", port=5002)