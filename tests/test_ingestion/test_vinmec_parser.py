from pathlib import Path

from src.medical_assistant.ingestion.crawlers.doctors.vinmec_crawler import language_for_url, read_urls_file
from src.medical_assistant.ingestion.crawlers.doctors.vinmec_parser import extract_profile_links, parse_profile


def test_extract_profile_links_filters_pagination_and_other_languages() -> None:
    html = """
    <a href="/vie/chuyen-gia-y-te/nguyen-van-a-123-vi">A</a>
    <a href="/vie/chuyen-gia-y-te/page_2">2</a>
    <a href="/eng/professionals/nguyen-van-a-123-en">English</a>
    """
    assert extract_profile_links(html, "https://www.vinmec.com/vie/chuyen-gia-y-te/", "vi") == [
        "https://www.vinmec.com/vie/chuyen-gia-y-te/nguyen-van-a-123-vi"
    ]


def test_parse_english_profile() -> None:
    html = """
    <section class="profile_doctor">
      <div class="col-5">
        <div class="avar_doctor">
          <img src="/doctor.jpg">
          <div class="bold cl-blue"><span>Ph.D</span><span>MD</span></div>
          <div class="f22 bold cl-blue mt1 mb1">Jane Doe</div>
        </div>
        <div class="desc_detail"><p>Emergency physician.</p></div>
      </div>
      <div class="col-7">
        <div><div class="f18 bold cl-blue">Specialties</div>
          <div class="mt1">Emergency</div><div class="line_ver"></div></div>
        <div class="mt40"><div><button class="collapsible">Experience</button>
          <div class="content"><p>Ten years at Vinmec</p></div></div></div>
      </div>
    </section>
    """
    result = parse_profile(
        html,
        "https://www.vinmec.com/eng/professionals/jane-doe-123-en",
        "en",
    )
    assert result["profile_id"] == "123"
    assert result["name"] == "Jane Doe"
    assert result["credentials"] == ["Ph.D", "MD"]
    assert result["specialties"] == ["Emergency"]
    assert result["experience"] == ["Ten years at Vinmec"]
    assert result["image_url"] == "https://www.vinmec.com/doctor.jpg"


def test_read_urls_file_groups_deduplicates_and_skips_unknown(tmp_path: Path) -> None:
    vi_url = "https://www.vinmec.com/vie/chuyen-gia-y-te/a-123-vi"
    en_url = "https://www.vinmec.com/eng/professionals/a-123-en"
    path = tmp_path / "urls_crawl.txt"
    path.write_text(
        f"# generated list\n{vi_url}\n{en_url}\n{vi_url}\nhttps://example.com/x\n",
        encoding="utf-8",
    )

    assert language_for_url(vi_url) == "vi"
    assert language_for_url(en_url) == "en"
    assert read_urls_file(path) == {"vi": [vi_url], "en": [en_url]}
