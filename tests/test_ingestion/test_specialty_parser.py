from src.medical_assistant.ingestion.crawlers.specialties.build_rag_documents import specialty_to_documents
from src.medical_assistant.ingestion.crawlers.specialties.specialty_parser import (
    extract_specialty_links,
    parse_specialty,
)


def test_extract_specialty_links_normalizes_and_filters() -> None:
    html = """
    <a href="/eng/specialties/cardiology-center//">Cardiology</a>
    <a href="/eng/specialties/">Index</a>
    <a href="/eng/professionals/a-1-en">Doctor</a>
    """
    assert extract_specialty_links(html, "https://www.vinmec.com/eng/specialties/", "en") == [
        "https://www.vinmec.com/eng/specialties/cardiology-center"
    ]


def test_parse_specialty_and_build_rag_documents() -> None:
    html = """
    <main>
      <div class="cover_list_news">
        <div class="name_cate_cover">Cardiology Center</div>
        <img src="/cover.jpg">
      </div>
      <section id="tong_quan" class="content_subcate">
        <div class="list_content_subcate">
          <img src="/overview.jpg">
          <div class="desc_subcate">
            <div class="tit_content_subcate">World-class care</div>
            <ul><li>International clinical standards.</li></ul>
          </div>
        </div>
      </section>
      <section id="bac_si"><a href="/eng/professionals/jane-doe-123-en">Jane</a></section>
    </main>
    """
    url = "https://www.vinmec.com/eng/specialties/cardiology-center"
    record = parse_specialty(html, url, "en")
    assert record["name"] == "Cardiology Center"
    assert record["overview"][0]["title"] == "World-class care"
    assert record["overview"][0]["content"] == ["International clinical standards."]
    assert record["doctor_urls"] == ["https://www.vinmec.com/eng/professionals/jane-doe-123-en"]

    documents = specialty_to_documents(record)
    assert documents[0]["chunk_id"] == ("vinmec-specialty-cardiology-center-en-overview-1-1")
    assert "## Overview" in documents[0]["text"]
    assert documents[0]["metadata"]["doctor_urls"] == record["doctor_urls"]
