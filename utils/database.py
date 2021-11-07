from datetime import datetime

from aiogram.types import User
from gino import Gino
from sqlalchemy import sql, Column, Text, Float, Integer, Sequence, BigInteger, String, Date

from data.config import DB_USER, DB_PASS, HOST

db = Gino()


class Dish(db.Model):
    __tablename__ = 'dishes'
    query: sql.Select
    update: sql.Select

    id = Column(Integer, Sequence('dish_id_seq'), primary_key=True)
    date = Column(Date)
    name = Column(String(100))
    price = Column(Integer)

    def __repr__(self):
        return f"<Dish(name='{self.name}', price='{self.price}')>"


class Customer(db.Model):
    __tablename__ = 'customers'
    query: sql.Select

    id = Column(Integer, Sequence('customer_id_seq'), primary_key=True)
    customer_id = Column(BigInteger, Sequence('customer_name_app_seq'), primary_key=True)
    pseudonym = Column(String(100))
    full_name = Column(String(100))
    credit = Column(Integer)

    def __repr__(self):
        return f"<Customer(id='{self.id}', full_name='{self.full_name}', " \
               f"username='{self.username}', credit='{self.credit}')>"


class DBCommands:
    @staticmethod
    async def get_customer(customer_id):
        customer = await Customer.query.where(Customer.customer_id == customer_id).gino.first()
        return customer

    async def add_new_customer(self, customer: User, customer_pseudonym):
        old_customer = await self.get_customer(customer.id)
        if old_customer:
            return
        new_customer = Customer()
        new_customer.customer_id = customer.id
        new_customer.pseudonym = customer_pseudonym
        new_customer.full_name = customer.full_name
        new_customer.credit = 0
        await new_customer.create()
        return new_customer

    @staticmethod
    async def get_dishes():
        dishes = await Dish.query.gino.all()
        return dishes

    @staticmethod
    async def delete_item(dish_name):
        await Dish.delete.where(Dish.name == dish_name).gino.status()

    @staticmethod
    async def update_name(dish_name, new_name):
        await Dish.update.values(name=new_name).where(Dish.name == dish_name).gino.status()

    @staticmethod
    async def update_price(dish_name, new_price):
        await Dish.update.values(price=new_price).where(Dish.name == dish_name).gino.status()

    @staticmethod
    async def del_dish_table():
        await Dish.delete.gino.all()


async def create_db():
    await db.set_bind(f"postgres://{DB_USER}:{DB_PASS}@{HOST}/menudb")
    await db.gino.drop_all()
    await db.gino.create_all()
    soup = Dish()
    soup.date = datetime.now()
    print(soup.date)
    soup.name = 'Суп'
    soup.price = 2000
    borsch = Dish()
    borsch.date = datetime.now()
    borsch.name = 'Борщ'
    borsch.price = 2500
    await soup.create()
    await borsch.create()

