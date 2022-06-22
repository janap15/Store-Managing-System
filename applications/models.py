from flask_sqlalchemy import SQLAlchemy

database = SQLAlchemy()


class ProductCategory(database.Model):
    __tablename__ = "productcategory"

    id = database.Column(database.Integer, primary_key=True)
    productId = database.Column(database.Integer, database.ForeignKey("products.id"), nullable=False)
    categoryId = database.Column(database.Integer, database.ForeignKey("categories.id"), nullable=False)

    def __repr__(self):
        return f"{self.productId} {self.categoryId}"


class ProductOrder(database.Model):
    __tablename__ = "productorder"

    id = database.Column(database.Integer, primary_key=True)
    productId = database.Column(database.Integer, database.ForeignKey("products.id"), nullable=False)
    orderId = database.Column(database.Integer, database.ForeignKey("orders.id"), nullable=False)
    requested = database.Column(database.Integer, nullable=False)
    received = database.Column(database.Integer, nullable=False)
    productPrice = database.Column(database.Float, nullable=False)

    def __repr__(self):
        return f"{self.productId} {self.orderId} {self.requested} {self.received} {self.productPrice}"


class Product(database.Model):
    __tablename__ = "products"

    id = database.Column(database.Integer, primary_key=True)
    name = database.Column(database.String(256), nullable=False, unique=True)
    price = database.Column(database.Float, nullable=False)
    quantity = database.Column(database.Integer, nullable=False)

    categories = database.relationship("Category", secondary=ProductCategory.__table__,
                                       back_populates="products")
    orders = database.relationship("Order", secondary=ProductOrder.__table__,
                                   back_populates="products")

    def __repr__(self):
        return self.name


class Category(database.Model):
    __tablename__ = "categories"

    id = database.Column(database.Integer, primary_key=True)
    name = database.Column(database.String(256), nullable=False)

    products = database.relationship("Product", secondary=ProductCategory.__table__,
                                     back_populates="categories")

    def __repr__(self):
        return self.name


class Order(database.Model):
    __tablename__ = "orders"

    id = database.Column(database.Integer, primary_key=True)
    price = database.Column(database.Float, nullable=False)
    status = database.Column(database.String(256), nullable=False)
    timestamp = database.Column(database.DateTime, nullable=False)
    customerEmail = database.Column(database.String(256), nullable=False)

    products = database.relationship("Product", secondary=ProductOrder.__table__,
                                     back_populates="orders")

    def __repr__(self):
        return str(self.id) + " " + str(self.products) + " " + self.status + " " + str(self.timestamp)
