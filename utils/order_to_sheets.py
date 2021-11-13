import pygsheets
import numpy as np

from pygsheets import SpreadsheetNotFound, cell

from data.config import SERVICE_FILE, SHARE_ADDRESS, FILE_NAME

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


def create_new_sheet(date: str, customers, dishes):
    sh = gc.open(FILE_NAME)
    wks = sh.add_worksheet(date)

    values = ['Наименование', 'Цена', 'Количество', 'x']
    for customer in customers:
        value = customer.pseudonym
        values.append(value)
    values.append('')
    wks.insert_rows(row=0, values=[values])

    num_col = len(values)
    f_string = f'=SUM(E2:{wks.cell((2, num_col)).label})'

    values = [['x', 'Всего сумма', '', ''], ['x', 'Всего кол-во', '', '']]
    for value in values:
        wks.insert_rows(row=1, values=[value])

    for dish in dishes:
        values = [dish.name, dish.price, f_string]
        wks.insert_rows(row=1, values=[values])

    rotating_cell = wks.cell((1, 4)).set_text_rotation(attribute='angle', value=90)
    while rotating_cell.value:
        rotating_cell = rotating_cell.neighbour(position='right')
        rotating_cell.set_text_rotation(attribute='angle', value=90)
    end_col = rotating_cell.col
    wks.adjust_column_width(start=1, end=end_col)
    wks.hide_dimensions(start=4, dimension='COLUMNS')
    print(wks.get_row(1, include_tailing_empty=False))


def add_order_to_sheet(user, order: dict):
    print(order)
    values = [user]
    for k, v in order.items():
        value = f'{k} x {v}'
        values.append(value)
    sh = gc.open(FILE_NAME)
    wks = sh.worksheets()[-1]
    # wks.insert_rows(row=0, number=2, values=[values])
    a = wks.range('A1:C5', returnas='cell')
    for b in a:
        for c in b:
            print(c.col)
    print(a)
    # names = np.array([f[0] for f in a])
    # cols = np.array(['Имя', 'Суп', 'Борщ'])
    # b = np.array(a)
    # print(b[names == 'Donald Trump', cols == 'Борщ'])

# {'Сало': 1, 'Хлеб': 1, 'Рыба': 1}
# todo pygsheets.exceptions.CellNotFound