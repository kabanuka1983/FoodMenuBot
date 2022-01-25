import pygsheets
import numpy as np

from pygsheets import SpreadsheetNotFound, Cell

from data.config import SERVICE_FILE, SHARE_ADDRESS, FILE_NAME
from utils.database import Customer, Dish

gc = pygsheets.authorize(service_file=SERVICE_FILE, scopes=('https://www.googleapis.com/auth/spreadsheets',
                                                            'https://www.googleapis.com/auth/drive'))


def create_file():
    if isinstance(SHARE_ADDRESS, list):
        adr_string = ''
        try:
            sh = gc.open(title=FILE_NAME)
            for adr in SHARE_ADDRESS:
                sh.share(email_or_domain=adr, role='writer')
                adr_string += f'{adr}\n'
            return f'Файл "{FILE_NAME}" открыт \nрасшарен для: \n{adr_string}'
        except SpreadsheetNotFound:
            sh = gc.create(title=FILE_NAME)
            for adr in SHARE_ADDRESS:
                sh.share(email_or_domain=adr, role='writer')
                adr_string += f'{adr}\n'
            return f'Файл "{FILE_NAME}" отсутствует и был создан \nрасшарен для: \n{adr_string}'
    if isinstance(SHARE_ADDRESS, str):
        try:
            sh = gc.open(title=FILE_NAME)
            sh.share(email_or_domain=SHARE_ADDRESS, role='writer')
            return f'Файл "{FILE_NAME}" открыт \nрасшарен для: \n{SHARE_ADDRESS}'
        except SpreadsheetNotFound:
            sh = gc.create(title=FILE_NAME)
            sh.share(email_or_domain=SHARE_ADDRESS, role='writer')
            return f'Файл "{FILE_NAME}" отсутствует и был создан \nрасшарен для: \n{SHARE_ADDRESS}'


def create_new_sheet(date: str, customers: list, dishes: Dish):
    # todo HttpError: <HttpError 400 when requesting
    customers.sort(key=lambda a: a.pseudonym)
    sh = gc.open(FILE_NAME)
    wks = sh.add_worksheet(title=date, index=0)

    values = [['', 'С-до на конец', '=SUM(D1:E1)'],
              ['', 'Всего сумма', '=SUM(D1:E1)'],
              ['', 'С-до на начало', '=SUM(D1:E1)'],
              ['', 'Всего кол-во', '=SUM(D1:E1)']]
    for value in values:
        wks.insert_rows(row=0, values=[value])
        wks.merge_cells(start=(1, 1), end=(1, 2))

    values = ['Наименование', 'Цена', 'Количество']
    wks.insert_rows(row=0, values=[values])
    for dish in dishes[::-1]:
        values = [dish.name, dish.price, '=SUM(D2:E2)']
        wks.insert_rows(row=1, values=[values])

    number_of_dishes = len(dishes)
    for customer in customers:
        values = [customer.pseudonym]
        for i in range(number_of_dishes):
            values.append('')
        values.append(f'=SUM(E2:E{number_of_dishes+1})')
        values.append(customer.credit)
        values.append('')
        values.append(f'=E{number_of_dishes+3}-E{number_of_dishes+4}')
        wks.insert_cols(col=4, values=values)
        f_string = '=0'
        for i in range(number_of_dishes):
            num_row = i + 2
            f_string += f'+E{num_row}*$B${num_row}'
        wks.cell((number_of_dishes+4, 5)).set_value(f_string)
    wks.hide_dimensions(start=4, dimension='COLUMNS')

    rotating_cell = wks.cell((1, 5))
    while rotating_cell.value:
        rotating_cell.set_text_rotation(attribute='angle', value=90)
        rotating_cell = rotating_cell.neighbour(position='right')
    end_col = rotating_cell.col
    wks.adjust_column_width(start=1, end=3)
    wks.adjust_column_width(start=4, end=end_col, pixel_size=34)


def cancel_order(pseudonym, date: str, dishes):
    sh = gc.open(FILE_NAME)
    wks = sh.worksheet(property='title', value=date)
    user_cell = wks.find(pseudonym, rows=(1, 1), matchEntireCell=True)[0]
    start_cell = (user_cell.row + 1, user_cell.col)
    end_cell = (user_cell.row + len(dishes), user_cell.col)
    total = wks.cell((user_cell.row + len(dishes) + 3, user_cell.col)).value_unformatted
    wks.clear(start_cell, end_cell)
    return int(total)


def get_rollback(date):
    sh = gc.open(FILE_NAME)
    wks = sh.worksheet(property='title', value=date)

    total_row: Cell = wks.find('Всего сумма', cols=(1, 1), matchEntireCell=True)[0]
    total_row_index = total_row.row
    order_cells = [c for c in wks.get_row(row=total_row_index, returnas='cell', include_tailing_empty=False)[4:]
                   if int(c.value) > 0]

    if len(order_cells) > 0:
        order_pseudonyms = [wks.cell((1, c.col)).value for c in order_cells]
        rollback_dict = dict(zip(order_pseudonyms, [int(c.value) for c in order_cells]))
        return rollback_dict
    else:
        return None


def delete_worksheet(date):
    sh = gc.open(FILE_NAME)
    wks = sh.worksheet(property='title', value=date)
    sh.del_worksheet(wks)


def add_order_to_sheet(customer, date, order: dict, dishes):
    np_dishes = np.array([d.name for d in dishes])

    sh = gc.open(FILE_NAME)
    wks = sh.worksheet(property='title', value=date)
    try:
        user_cell = wks.find(customer.pseudonym, rows=(1, 1), matchEntireCell=True)[0]
    except IndexError:
        user_cell = add_new_customer_to_sheet(customer=customer, date=date, dishes=dishes)
    start_cell = (user_cell.row + 1, user_cell.col)
    end_cell = (user_cell.row + len(dishes), user_cell.col)
    order_range = wks.get_values(start_cell, end_cell, returnas='cell', include_tailing_empty_rows=True)
    np_range = np.array(order_range)
    order.pop('order_message')
    for k, v in order.items():
        if v[1]:
            order_cell = np_range[np_dishes == k][0][0].label
            wks.update_value(order_cell, v[1])
    total = wks.cell((user_cell.row + len(dishes) + 3, user_cell.col)).value_unformatted
    return int(total)


def get_order_from_sheet(pseudonym: Customer.pseudonym, date, dishes):
    np_dishes = np.array([d.name for d in dishes])

    sh = gc.open(FILE_NAME)
    wks = sh.worksheet(property='title', value=date)
    user_cell = wks.find(pseudonym, rows=(1, 1), matchEntireCell=True)[0]
    # IndexError: list index out of range если есть 1 в Customer.current_order, но нет имени в таблице
    start_cell = (user_cell.row + 1, user_cell.col)
    end_cell = (user_cell.row + len(dishes), user_cell.col)
    order_range = wks.get_values(start_cell, end_cell, returnas='cell', include_tailing_empty_rows=True)
    np_range = np.array(order_range)
    order_dict = {}
    for dish in dishes:
        d = dish.name
        dval = np_range[np_dishes == d][0][0].value_unformatted
        order_dict[d] = dval if dval != '' else None
    return order_dict


def add_new_customer_to_sheet(customer: Customer, date, dishes: Dish):
    sh = gc.open(FILE_NAME)
    wks = sh.worksheet(property='title', value=date)
    number_of_dishes = len(dishes)
    values = [customer.pseudonym]
    for i in range(number_of_dishes):
        values.append('')
    values.append(f'=SUM(E2:E{number_of_dishes + 1})')
    values.append(customer.credit)
    values.append('')
    values.append(f'=E{number_of_dishes + 3}-E{number_of_dishes + 4}')
    wks.insert_cols(col=4, values=values)
    f_string = '=0'
    for i in range(number_of_dishes):
        num_row = i + 2
        f_string += f'+E{num_row}*$B${num_row}'
    wks.cell((number_of_dishes + 4, 5)).set_value(f_string)
    return Cell((1, 5))


def update_worksheet_pseudonym(old_pseudonym, new_pseudonym, date: str):
    sh = gc.open(FILE_NAME)
    wks = sh.worksheet(property='title', value=date)
    pseudonym_cell: list = wks.find(old_pseudonym)
    if len(pseudonym_cell) > 0:
        pseudonym_cell[0].set_value(new_pseudonym)


# todo pygsheets.exceptions.CellNotFound