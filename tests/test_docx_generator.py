from docx import Document

from src.docx_generator import DocxGenerator, extract_docx_text


def test_docx_generator_creates_docx_from_template(tmp_path):
    template_path = tmp_path / "template.docx"
    output_path = tmp_path / "result.docx"
    document = Document()
    document.add_paragraph("Сотрудник: {{ employee.full_name }}")
    document.save(template_path)

    result = DocxGenerator().render(template_path, {"employee": {"full_name": "Иванов Иван"}}, output_path)

    assert result.exists()
    assert "Иванов Иван" in extract_docx_text(result)

