from src.medical_assistant.ingestion.crawlers.hospitals.hospital_parser import (
    normalize_hotline,
    parse_facilities,
)


def test_normalize_hotline() -> None:
    assert normalize_hotline("(+84 29) 2368 3003") == "842923683003"


def test_parse_hospital_and_clinic_cards() -> None:
    html = """
    <main>
      <section class="bottom_news_main">
        <h2 class="title_cate_news">Hospitals</h2>
        <div class="list_hospital_main">
          <div class="col-4"><div class="content_news_hor">
            <a class="name_hospital" href="/eng/hospital/times-city">Times City Hospital
              <div class="view_more_hospital">View more</div>
            </a>
            <div class="address_hospital">458 Minh Khai, Hanoi</div>
            <div class="phone_hospital">024 3974 3556</div>
          </div></div>
        </div>
      </section>
      <section class="bottom_news_main">
        <h2 class="title_cate_news">Clinics</h2>
        <div class="list_hospital_main">
          <div class="col-4"><div class="content_news_hor">
            <a class="name_hospital" href="/eng/hospital/royal-city">Royal City Clinic</a>
            <div class="address_hospital">72A Nguyen Trai, Hanoi</div>
            <div class="phone_hospital">024 3975 6887</div>
          </div></div>
        </div>
      </section>
    </main>
    """
    records = parse_facilities(html, "https://www.vinmec.com/eng/hospital/", "en")
    assert len(records) == 2
    assert records[0]["facility_type"] == "hospital"
    assert records[0]["name"] == "Times City Hospital"
    assert records[0]["hotline_normalized"] == "02439743556"
    assert records[1]["facility_type"] == "clinic"
    assert records[1]["detail_url"] == "https://www.vinmec.com/eng/hospital/royal-city"
