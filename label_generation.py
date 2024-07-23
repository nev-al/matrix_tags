from pylibdmtx import pylibdmtx
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, Frame
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, mm
import reportlab.lib.enums
from csv_handler import *
from PIL import Image
from io import BytesIO


def generate_datamatrix(code, size='SquareAuto'):
    encoder = pylibdmtx.encode(code.encode('utf-8'), size=size)
    img = Image.frombytes('RGB', (encoder.width, encoder.height), encoder.pixels)
    return img


def generate_label_full_info(csv_file_path, filename='test_label_bigger.pdf'):
    label_width, label_height = 235, 350
    c = canvas.Canvas(filename, pagesize=(label_width, label_height))
    pdfmetrics.registerFont(TTFont('DejaVuSerif', 'DejaVuSerif.ttf'))
    c.setFont('DejaVuSerif', 12)
    pdfmetrics.registerFont(TTFont('DejaVuSerif-Bold', 'DejaVuSerif-Bold.ttf'))
    styles = getSampleStyleSheet()
    normal_style = styles['BodyText']
    title_style = ParagraphStyle('Title', parent=normal_style, fontName='DejaVuSerif-Bold', fontSize=12)
    dmtx_decoded_str_style = ParagraphStyle('Caption', alignment=reportlab.lib.enums.TA_CENTER,
                                            parent=normal_style, fontName='DejaVuSerif-Bold', fontSize=5, leading=5)
    index_str_style = ParagraphStyle('Index', alignment=reportlab.lib.enums.TA_LEFT,
                                     parent=normal_style, fontName='DejaVuSerif-Bold', fontSize=10)

    datamatrix_multiplier = 0.2  # Adjust this value to change the size of the data matrix
    datamatrix_size = min(label_width, label_height) * datamatrix_multiplier

    with open(csv_file_path) as csvfile:
        reader = csv.reader(csvfile, delimiter='\t', quoting=csv.QUOTE_NONE, escapechar='\\')
        data = list(reader)

    index = 1

    for entry in data:
        code, name, size, unit_type, sex, madeof, color, model, country, tp_ts = entry
        img = generate_datamatrix(code)
        img_bytes = BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)

        f_image = Frame(label_width - (datamatrix_size + 10), label_height - (datamatrix_size + 1),
                        (datamatrix_size + 10), (datamatrix_size + 1), leftPadding=0, bottomPadding=0, rightPadding=0,
                        topPadding=1, id=None, showBoundary=0)
        f_image.addFromList(
            [reportlab.platypus.Image(img_bytes, width=datamatrix_size, height=datamatrix_size), ], c)

        f = Frame(0, label_height - (datamatrix_size + 15),
                  label_width - (datamatrix_size + 10), (datamatrix_size + 15), id=None, showBoundary=0)
        f.addFromList([Paragraph(f'{name}', title_style), ], c)

        f_caption = Frame(label_width - (datamatrix_size + 10), label_height - (datamatrix_size + 15),
                          (datamatrix_size + 10), 14, leftPadding=0, bottomPadding=0, rightPadding=0,
                          topPadding=0, id=None, showBoundary=0)
        # TODO: reportlab paraparser.py works fine? check escape with symbols like '<'
        f_caption.addFromList([Paragraph(
            code[:30].replace('<', '< '), dmtx_decoded_str_style), ], c)

        c.line(0, label_height - (datamatrix_size + 17), label_width, label_height - (datamatrix_size + 17))

        f_table = Frame(0, 0, label_width, label_height - (datamatrix_size + 18), leftPadding=0,
                        bottomPadding=0, rightPadding=0, topPadding=0, id=None, showBoundary=0)
        table_data = [['Размер', size],
                      ['Вид изделия', unit_type],
                      ['Целевой пол', sex],
                      ['Состав', madeof],
                      ['Цвет', color],
                      ['Модель', model],
                      ['Страна', country],
                      ['ТР ТС', tp_ts], ]
        tbl = reportlab.platypus.Table(data=table_data, colWidths=110, rowHeights=30)
        tbl.setStyle(reportlab.platypus.TableStyle([('ALIGN', (0, 0), (0, -1), 'LEFT'),
                                                    ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                                                    ('FONT', (0, 0), (0, -1), 'DejaVuSerif-Bold'),
                                                    ('FONT', (1, 0), (1, -1), 'DejaVuSerif'),
                                                    ('LINEBELOW', (0, 0), (-1, -1), 0.1, reportlab.lib.styles.black),

                                                    ]))
        f_table.addFromList([tbl, ], c)

        f_index = Frame(3, 3, 100, 20, leftPadding=0, bottomPadding=0, rightPadding=0,
                        topPadding=3, id=None, showBoundary=0)
        f_index.addFromList([Paragraph(f'#{index}', index_str_style), ], c)

        f_eac_image = Frame(label_width - 45, 3, 40, 30, leftPadding=0,
                            bottomPadding=0, rightPadding=0, topPadding=0, id=None, showBoundary=0)
        f_eac_image.addFromList([reportlab.platypus.Image('data/demo_samples/eac_image.png',
                                                          width=30, height=30)], c)

        c.showPage()
        index += 1

    c.save()


def generate_label_15_20mm_per_page(csv_file_path, label_size, output_file, index_on):
    label_width = label_height = label_size * mm
    c = canvas.Canvas(output_file, pagesize=(label_width, label_height))
    pdfmetrics.registerFont(TTFont('DejaVuSerif', 'DejaVuSerif.ttf'))
    pdfmetrics.registerFont(TTFont('DejaVuSerif-Bold', 'DejaVuSerif-Bold.ttf'))
    datamatrix_size = label_size * mm
    index = 1
    with open(csv_file_path) as file:
        data_codes = file.readlines()
        for string in data_codes:
            result = find_datacode(string)
            if result:
                img = generate_datamatrix(result)
                img_bytes = BytesIO()
                img.save(img_bytes, format='PNG')
                img_bytes.seek(0)
                f_image = Frame(0, 0, label_width, label_height, leftPadding=0, bottomPadding=0, rightPadding=0,
                                topPadding=0, showBoundary=0)
                f_image.addFromList(
                    [reportlab.platypus.Image(img_bytes, width=datamatrix_size, height=datamatrix_size), ], c)
                if index_on:
                    c.setFont('DejaVuSerif-Bold', 3)
                    c.drawString(datamatrix_size // 2, 0, f'{index}')
                c.showPage()
                index += 1
    c.save()


def generate_label_15_20mm_paving_a4(csv_file_path, label_size, output_file, index_on):
    MAX_PIECES = 266 if label_size == 15 else 140
    label_width, label_height = A4
    c = canvas.Canvas(output_file, pagesize=(label_width, label_height))
    datamatrix_size = label_size * mm
    frames_list = []
    images_list = []
    with open(csv_file_path) as file:
        data_codes = file.readlines()
        for string in data_codes:
            result = find_datacode(string)
            if result:
                img = generate_datamatrix(result)
                img_bytes = BytesIO()
                img.save(img_bytes, format='PNG')
                img_bytes.seek(0)
                images_list.append(reportlab.platypus.Image(img_bytes, width=datamatrix_size, height=datamatrix_size))
                # f_image.addFromList(
                #     [reportlab.platypus.Image(img_bytes, width=datamatrix_size, height=datamatrix_size), ], c)

    index = 1
    for img_index in range(len(images_list)):
        if img_index // MAX_PIECES > 0 and img_index % MAX_PIECES == 0:
            c.showPage()
        coords = divide_sheet(label_size)
        for coord in coords:
            frames_list.append(
                Frame(coord[0], coord[1], coord[2], coord[3], leftPadding=0, bottomPadding=0,
                      rightPadding=0, topPadding=0, showBoundary=0))
        # f_image = Frame(0, 0, label_width, label_height, leftPadding=1, bottomPadding=1, rightPadding=1,
        #                 topPadding=1, showBoundary=1)
        frames_list[img_index].addFromList([images_list[img_index]], c)
        # frames_list[img_index].addFromList([Paragraph(f'{index}'), ], c)
        index += 1
    c.save()


def generate_label_15_20mm(csv_file_path, label_size, output_file, index_on, paving):
    if paving:
        generate_label_15_20mm_paving_a4(csv_file_path, label_size, output_file, index_on)
    else:
        generate_label_15_20mm_per_page(csv_file_path, label_size, output_file, index_on)


def divide_sheet(dmtx_size=20):
    sheet_width, sheet_height = A4
    piece_width = dmtx_size * mm
    piece_height = dmtx_size * mm
    if piece_width <= 0 or piece_height <= 0:
        raise ValueError("Piece dimensions must be positive numbers.")

    if piece_width > sheet_width or piece_height > sheet_height:
        raise ValueError("Piece size cannot be larger than sheet size.")

    num_pieces_width = int(sheet_width // piece_width)
    num_pieces_height = int(sheet_height // piece_height)

    total_pieces = num_pieces_width * num_pieces_height

    piece_info = []
    for i in range(num_pieces_height):
        for j in range(num_pieces_width):
            x = j * piece_width
            y = i * piece_height
            piece_info.append((x, y, piece_width, piece_height))

    return piece_info


if __name__ == '__main__':
    # generate_label_full_info('/home/usr/PycharmProjects/matrix_tags/data/test/joined_170141723.csv')
    generate_label_15_20mm_per_page(csv_file_path='data/user_722178606/csv_29c90f25-fb8a-4bed-b3dc-a7bb45ade39e.csv',
                                    label_size=20, output_file='output.pdf', index_on=True)