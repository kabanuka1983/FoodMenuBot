from aiogram.dispatcher.filters.state import StatesGroup, State


class Order(StatesGroup):
    main = State()
    dishes_dict = State()
    checkout = State()


class NewItem(StatesGroup):
    name = State()
    price = State()
    approve = State()


class ChangeItem(StatesGroup):
    item = State()
    name = State()
    price = State()


class AdminMenu(StatesGroup):
    panel = State()
    change = State()


class RegMenu(StatesGroup):
    reg_name = State()
    reg_surname = State()

