import base64
import io
import zipfile

import pymupdf
import pytest
from fastapi.testclient import TestClient
from PIL import Image

import app as application
from server.documents import DocumentError, import_document


@pytest.fixture
def client():
    return TestClient(application.app)


def make_pdf(count=7, bookmarks=True, password=None):
    with pymupdf.open() as pdf:
        for index in range(count):
            page = pdf.new_page(width=500, height=300)
            page.insert_text((45, 100), f"Focus slide {index + 1}", fontsize=28)
        if bookmarks:
            pdf.set_toc([[1, "Getting started", 1], [1, "Going deeper", 4]])
        if password:
            return pdf.tobytes(encryption=pymupdf.PDF_ENCRYPT_AES_256, owner_pw=password, user_pw=password)
        return pdf.tobytes()


def test_python_import_renders_pages_and_honors_pdf_sections(client):
    response = client.post('/api/import', files={'file': ('Focus notes.pdf', make_pdf(), 'application/pdf')})
    assert response.status_code == 200
    deck = response.json()
    assert deck['title'] == 'Focus notes'
    assert len(deck['slides']) == 7
    assert [(s['title'], s['start'], s['end']) for s in deck['sections']] == [('Getting started', 0, 2), ('Going deeper', 3, 6)]
    assert deck['slides'][0]['title'] == 'Focus slide 1'
    rendered = Image.open(io.BytesIO(base64.b64decode(deck['slides'][0]['image'].split(',')[1])))
    assert rendered.width == 850 and rendered.height == 510
    assert rendered.convert('L').getextrema()[0] < 100  # Actual text was rendered.


def test_bookmarkless_pdf_gets_manageable_sections():
    deck = import_document('notes.PDF', make_pdf(bookmarks=False))
    assert [(s['start'], s['end']) for s in deck['sections']] == [(0, 4), (5, 6)]


@pytest.mark.parametrize('filename,data,message', [
    ('notes.txt', b'hello', 'Choose a PDF'),
    ('broken.pdf', b'not a pdf', 'could not be opened'),
    ('empty.pdf', b'', 'empty'),
    ('broken.png', b'bad image', 'image could not be opened'),
    ('bad.pptx', b'bad zip', 'presentation could not be opened'),
])
def test_bad_uploads_report_actionable_errors(client, filename, data, message):
    response = client.post('/api/import', files={'file': (filename, data)})
    assert response.status_code == 422
    assert message in response.json()['detail']


def test_password_protected_pdf_is_rejected(client):
    response = client.post('/api/import', files={'file': ('locked.pdf', make_pdf(password='secret'))})
    assert response.status_code == 422
    assert 'password protected' in response.json()['detail']


def test_page_limit_is_enforced():
    with pytest.raises(DocumentError, match='1–300'):
        import_document('large.pdf', make_pdf(count=301, bookmarks=False))


def test_image_import_is_decoded_and_sanitized():
    data = io.BytesIO()
    Image.new('RGB', (300, 180), '#b4503d').save(data, format='PNG')
    deck = import_document('../../a-slide.png', data.getvalue())
    assert deck['filename'] == 'a-slide.png'
    assert deck['kind'] == 'image' and len(deck['slides']) == 1
    assert deck['slides'][0]['image'].startswith('data:image/webp;base64,')


def test_powerpoint_uses_presentation_order():
    data = io.BytesIO()
    with zipfile.ZipFile(data, 'w') as archive:
        for index in [1, 2]:
            archive.writestr(f'ppt/slides/slide{index}.xml', f'<s xmlns:a="urn:a"><a:p><a:r><a:t>Idea {index}</a:t></a:r></a:p></s>')
        archive.writestr('ppt/presentation.xml', '<p:presentation xmlns:p="urn:p" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><p:sldIdLst><p:sldId r:id="two"/><p:sldId r:id="one"/></p:sldIdLst></p:presentation>')
        archive.writestr('ppt/_rels/presentation.xml.rels', '<Relationships><Relationship Id="one" Target="slides/slide1.xml"/><Relationship Id="two" Target="slides/slide2.xml"/></Relationships>')
    deck = import_document('slides.pptx', data.getvalue())
    assert [s['title'] for s in deck['slides']] == ['Idea 2', 'Idea 1']


def test_untrusted_xml_is_rejected(client):
    data = io.BytesIO()
    with zipfile.ZipFile(data, 'w') as archive:
        archive.writestr('ppt/slides/slide1.xml', '<!DOCTYPE s [<!ENTITY content SYSTEM "file:///etc/passwd">]><s>&content;</s>')
    response = client.post('/api/import', files={'file': ('untrusted.pptx', data.getvalue())})
    assert response.status_code == 422


def test_upload_size_and_cross_origin_requests(client, monkeypatch):
    monkeypatch.setattr(application, 'MAX_BYTES', 100)
    assert client.post('/api/import', files={'file': ('test.pdf', b'x' * 101)}).status_code == 413
    response = client.post('/api/import', files={'file': ('test.pdf', b'x')}, headers={'Origin': 'https://different.example'})
    assert response.status_code == 403


def test_python_serves_ui_and_api(client):
    assert client.get('/api/health').json()['backend'] == 'python'
    assert client.get('/api/missing').status_code == 404
    response = client.get('/')
    assert response.status_code == 200
    assert 'note that' in response.text and '/assets/index-' in response.text
