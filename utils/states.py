from aiogram.dispatcher.filters.state import StatesGroup, State


class Order(StatesGroup):
    main = State()
    dishes_dict = State()
    checkout = State()


class AdminMenu(StatesGroup):
    panel = State()
    change = State()
    instance_menu = State()
    credit = State()
    credit_push = State()
    credit_upd = State()
    # cancel = State()
    rollback = State()


class RegMenu(StatesGroup):
    reg_name = State()
    reg_surname = State()


class ChangePseudonym(StatesGroup):
    initial = State()
    name = State()
    surname = State()

