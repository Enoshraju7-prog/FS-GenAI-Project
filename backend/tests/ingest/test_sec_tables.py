from ingest.sec_tables import extract_sec_tables


def test_extract_simple_table_with_title_and_units():
    html = """
    <html><body>
    <p>The following table shows revenue by segment (in millions):</p>
    <table>
      <tr><td>Metric</td><td>2024</td><td>2023</td></tr>
      <tr><td>Segment A</td><td>$100</td><td>$90</td></tr>
      <tr><td>Segment B</td><td>$50</td><td>$40</td></tr>
    </table>
    </body></html>
    """
    tables = extract_sec_tables(html)

    assert len(tables) == 1
    table = tables[0]
    assert table.units == "in millions"
    assert [c.label for c in table.columns] == ["Metric", "2024", "2023"]
    assert table.rows[0].label == "Segment A"
    assert [cell.text for cell in table.rows[0].cells] == ["$100", "$90"]


def test_extract_sales_change_table():
    html = """
    <table>
      <tr><td>Category</td><td>2024</td><td>Change</td><td>2023</td><td>Change</td></tr>
      <tr><td>Total net sales</td><td>$</td><td>391,035</td><td>2</td><td>%</td>
          <td>$</td><td>383,285</td><td>(3)</td><td>%</td></tr>
    </table>
    """
    tables = extract_sec_tables(html)

    assert len(tables) == 1
    row = tables[0].rows[0]
    assert row.label == "Total net sales"
    values = [cell.text for cell in row.cells]
    assert values == ["$391,035", "2%", "$383,285", "(3)%"]


def test_non_meaningful_table_is_skipped():
    html = """
    <table>
      <tr><td>Header</td><td>Value</td></tr>
      <tr><td>Some label</td><td>Not a number</td></tr>
    </table>
    """
    tables = extract_sec_tables(html)

    assert tables == []


def test_inline_xbrl_facts_captured():
    html = """
    <table>
      <tr><td>Metric</td><td>2024</td></tr>
      <tr><td>Total net sales</td>
          <td><ix:nonfraction name="us-gaap:Revenues" contextref="c1" unitref="usd" decimals="-6">391,035</ix:nonfraction></td></tr>
    </table>
    """
    tables = extract_sec_tables(html)

    assert len(tables) == 1
    cell = tables[0].rows[0].cells[0]
    assert cell.text == "391,035"
    assert len(cell.facts) == 1
    fact = cell.facts[0]
    assert fact.name == "us-gaap:Revenues"
    assert fact.unit_ref == "usd"
    assert fact.decimals == "-6"


def test_footnote_extraction():
    html = """
    <table>
      <tr><td>Metric</td><td>2024</td></tr>
      <tr><td>China (1)</td><td>$66,952</td></tr>
    </table>
    <p>(1) China includes Hong Kong and Taiwan.</p>
    """
    tables = extract_sec_tables(html)

    assert len(tables) == 1
    assert tables[0].footnotes == ["(1) China includes Hong Kong and Taiwan."]


def test_source_html_hash_is_stable_sha256():
    html = "<table><tr><td>A</td><td>1</td></tr><tr><td>B</td><td>2</td></tr></table>"
    first = extract_sec_tables(html)
    second = extract_sec_tables(html)

    assert first[0].source_html_hash == second[0].source_html_hash
    assert len(first[0].source_html_hash) == 64
