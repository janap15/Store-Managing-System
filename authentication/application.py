from flask import Flask, request, Response, jsonify
from configuration import Configuration
from models import database, User, Role
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, create_refresh_token, get_jwt, get_jwt_identity
from sqlalchemy import and_
import re

application = Flask(__name__)
application.config.from_object(Configuration)


@application.route("/register", methods=["POST"])
def register():
    forename = request.json.get("forename", "")
    surname = request.json.get("surname", "")
    email = request.json.get("email", "")
    password = request.json.get("password", "")
    isCustomer = request.json.get("isCustomer", None)

    forenameEmpty = len(forename) == 0
    surnameEmpty = len(surname) == 0
    emailEmpty = len(email) == 0
    passwordEmpty = len(password) == 0
    isCustomerNone = isCustomer is None

    if forenameEmpty:
        return jsonify(message="Field forename is missing."), 400

    if surnameEmpty:
        return jsonify(message="Field surname is missing."), 400

    if emailEmpty:
        return jsonify(message="Field email is missing."), 400

    if passwordEmpty:
        return jsonify(message="Field password is missing."), 400

    if isCustomerNone:
        return jsonify(message="Field isCustomer is missing."), 400

    if not re.fullmatch(r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-z|A-Z]{2,}\b', email):
        return jsonify(message="Invalid email."), 400

    if not re.fullmatch(r"(?=.*[A-Z])(?=.*[a-z])(?=.*\d)[A-Za-z\d]{8,}", password):
        return jsonify(message="Invalid password."), 400

    if not User.query.filter(User.email == email).first() is None:
        return jsonify(message="Email already exists."), 400

    if isCustomer:
        role = Role.query.filter(Role.name == "customer").first()
    else:
        role = Role.query.filter(Role.name == "manager").first()

    user = User(
        forename=forename,
        surname=surname,
        email=email,
        password=password,
        roleId=role.id
    )
    database.session.add(user)
    database.session.commit()

    return Response(status=200)


jwt = JWTManager(application)


@application.route("/login", methods=["POST"])
def login():
    email = request.json.get("email", "")
    password = request.json.get("password", "")

    emailEmpty = len(email) == 0
    passwordEmpty = len(password) == 0

    if emailEmpty:
        return jsonify(message="Field email is missing."), 400

    if passwordEmpty:
        return jsonify(message="Field password is missing."), 400

    if not re.fullmatch(r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-z|A-Z]{2,}\b', email):
        return jsonify(message="Invalid email."), 400

    user = User.query.filter(and_(User.email == email, User.password == password)).first()

    if not user:
        return jsonify(message="Invalid credentials."), 400

    additionalClaims = {
        "forename": user.forename,
        "surname": user.surname,
        "role": str(user.role),
        "email": user.email
    }

    accessToken = create_access_token(identity=user.email, additional_claims=additionalClaims)
    refreshToken = create_refresh_token(identity=user.email, additional_claims=additionalClaims)

    return jsonify(accessToken=accessToken, refreshToken=refreshToken), 200


@application.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    identity = get_jwt_identity()
    refreshClaims = get_jwt()

    additionalClaims = {
        "forename": refreshClaims["forename"],
        "surname": refreshClaims["surname"],
        "role": refreshClaims["role"],
        "email": refreshClaims["email"]
    }

    accessToken = create_access_token(identity=identity, additional_claims=additionalClaims)

    return jsonify(accessToken=accessToken), 200


@application.route("/delete", methods=["POST"])
@jwt_required()
def delete():
    claims = get_jwt()

    if "admin" != claims["role"] or "role" not in claims:
        return jsonify(msg="Missing Authorization Header"), 401

    email = request.json.get("email", "")
    emailEmpty = len(email) == 0

    if emailEmpty:
        return jsonify(message="Field email is missing."), 400

    if not re.fullmatch(r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-z|A-Z]{2,}\b', email):
        return jsonify(message="Invalid email."), 400

    user = User.query.filter(User.email == email).first()
    if user is None:
        return jsonify(message="Unknown user."), 400

    database.session.delete(user)
    database.session.commit()

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
    con.execute('ALTER TABLE users AUTO_INCREMENT=1;')
    con.execute('ALTER TABLE roles AUTO_INCREMENT=1;')
    trans.commit()

    adminRole = Role(name="admin")
    customerRole = Role(name="customer")
    warehouseRole = Role(name="manager")

    database.session.add(adminRole)
    database.session.add(customerRole)
    database.session.add(warehouseRole)
    database.session.commit()

    admin = User(
        forename="admin",
        surname="admin",
        email="admin@admin.com",
        password="1",
        roleId=adminRole.id
    )

    database.session.add(admin)
    database.session.commit()

    return str(User.query.all()) + "<br>" + str(Role.query.all())


if __name__ == "__main__":
    database.init_app(application)
    application.run(debug=True, host="0.0.0.0", port=5000)
