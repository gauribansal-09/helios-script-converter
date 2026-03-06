from helios_converter.models import ConversionResult, QueryMatch


class TestConversionResult:
    def test_required_fields(self) -> None:
        r = ConversionResult(file="script.py", file_type="Python")
        assert r.file == "script.py"
        assert r.file_type == "Python"

    def test_defaults(self) -> None:
        r = ConversionResult(file="script.py", file_type="Python")
        assert r.output is None
        assert r.queries_processed == 0
        assert r.success is True
        assert r.error is None
        assert r.changes == []

    def test_changes_not_shared_between_instances(self) -> None:
        a = ConversionResult(file="a.py", file_type="Python")
        b = ConversionResult(file="b.py", file_type="Python")
        a.changes.append("change 1")
        assert b.changes == []

    def test_all_fields(self) -> None:
        r = ConversionResult(
            file="query.sql",
            file_type="SQL",
            output="output/query.sql",
            queries_processed=3,
            success=False,
            error="parse error",
            changes=["removed WAREHOUSE clause"],
        )
        assert r.output == "output/query.sql"
        assert r.queries_processed == 3
        assert r.success is False
        assert r.error == "parse error"
        assert r.changes == ["removed WAREHOUSE clause"]


class TestQueryMatch:
    def test_required_fields(self) -> None:
        q = QueryMatch(query_text="SELECT 1", line_number=10, quote_type="double")
        assert q.query_text == "SELECT 1"
        assert q.line_number == 10
        assert q.quote_type == "double"

    def test_defaults(self) -> None:
        q = QueryMatch(query_text="SELECT 1", line_number=1, quote_type="single")
        assert q.variable_name is None
        assert q.converted_query is None
        assert q.conversion_successful is False
        assert q.conversion_error is None

    def test_all_fields(self) -> None:
        q = QueryMatch(
            query_text="SELECT * FROM ORDERS",
            line_number=42,
            quote_type="triple_double",
            variable_name="sql",
            converted_query="SELECT * FROM orders",
            conversion_successful=True,
            conversion_error=None,
        )
        assert q.variable_name == "sql"
        assert q.converted_query == "SELECT * FROM orders"
        assert q.conversion_successful is True
