from io import BytesIO
from collections import defaultdict
from datetime import datetime
import re

from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn


class WordExportService:
    """
    Premium Library Catalogue Word export (English & Indian Authors).

    Structure:
        Cover
        Index / Contents
        Blank separator page
        Category 1
            Authors
                Books + Price
            "Books I've Read" writing page
        Category 2
            ...
            "Books I've Read" writing page
        ...

    The database is never modified. Serial numbers are normalized only
    for presentation in the Word document (e.g. 25.0 -> 25).
    """

    # ------------------------------------------------------------------
    # CATEGORY ORDER
    # ------------------------------------------------------------------
    # Subcategories are discovered directly from the database.
    CATEGORY_ORDER = [
        "Autobiographies Tamil",
        "Religious Books Tamil",
        "Self development Tamil"
    ]
    # Premium restrained palette
    NAVY = "17324D"
    DEEP_NAVY = "10263A"
    GOLD = "B08D57"
    LIGHT_GOLD = "EFE4D2"
    PALE_GOLD = "F8F4EE"
    WARM_WHITE = "FCFBF8"
    CHARCOAL = "242A30"
    GREY = "69737D"
    LIGHT_GREY = "DDE2E6"
    VERY_LIGHT = "F2F4F5"
    WHITE = "FFFFFF"

    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_category(value: str) -> str:
        value = str(value or "").strip()
        return re.sub(r"\s+", " ", value).casefold()

    @staticmethod
    def _display_category(value: str) -> str:
        value = str(value or "Uncategorized").strip()
        return re.sub(r"\s+", " ", value)

    @staticmethod
    def _normalize_serial(value) -> str:
        """
        Presentation-only normalization.

        1.0  -> 1
        25.0 -> 25
        25.00 -> 25
        10A -> 10A
        10-A -> 10-A
        ABC -> ABC
        """
        if value is None:
            return ""

        text = str(value).strip()

        if not text:
            return ""

        # Remove decimal suffix only when it is a whole number.
        match = re.fullmatch(r"([+-]?\d+)\.0+", text)
        if match:
            return match.group(1)

        return text

    @staticmethod
    def _serial_sort_key(book):
        raw = str(book.get("serial_number") or "").strip()

        if not raw:
            return (3, float("inf"), "")

        # Numeric values: 1, 2, 10, 25.0
        if re.fullmatch(r"\d+(?:\.0+)?", raw):
            try:
                return (0, float(raw), "")
            except ValueError:
                pass

        # Numeric + suffix: 10A, 10B, 25-A
        match = re.match(r"^(\d+)\s*(.*)$", raw)
        if match:
            try:
                number = int(match.group(1))
                suffix = match.group(2).strip().casefold()
                return (1, number, suffix)
            except ValueError:
                pass

        return (2, float("inf"), raw.casefold())

    @staticmethod
    def _price_text(price) -> str:
        if price is None or str(price).strip() == "":
            return "—"

        try:
            numeric = float(price)
            if numeric.is_integer():
                return f"₹{int(numeric):,}"
            return f"₹{numeric:,.2f}"
        except (ValueError, TypeError):
            return str(price)

    @staticmethod
    def _set_cell_shading(cell, fill: str):
        tc_pr = cell._tc.get_or_add_tcPr()
        shd = tc_pr.find(qn("w:shd"))

        if shd is None:
            shd = OxmlElement("w:shd")
            tc_pr.append(shd)

        shd.set(qn("w:fill"), fill)

    @staticmethod
    def _set_cell_margins(cell, top=80, start=100, bottom=80, end=100):
        tc = cell._tc
        tc_pr = tc.get_or_add_tcPr()

        tc_mar = tc_pr.first_child_found_in("w:tcMar")
        if tc_mar is None:
            tc_mar = OxmlElement("w:tcMar")
            tc_pr.append(tc_mar)

        for margin, value in (
            ("top", top),
            ("start", start),
            ("bottom", bottom),
            ("end", end),
        ):
            node = tc_mar.find(qn(f"w:{margin}"))
            if node is None:
                node = OxmlElement(f"w:{margin}")
                tc_mar.append(node)
            node.set(qn("w:w"), str(value))
            node.set(qn("w:type"), "dxa")

    @staticmethod
    def _set_cell_border(cell, color="DDE2E6", size="4"):
        tc_pr = cell._tc.get_or_add_tcPr()
        borders = tc_pr.first_child_found_in("w:tcBorders")

        if borders is None:
            borders = OxmlElement("w:tcBorders")
            tc_pr.append(borders)

        for edge in ("top", "left", "bottom", "right"):
            tag = qn(f"w:{edge}")
            element = borders.find(tag)

            if element is None:
                element = OxmlElement(f"w:{edge}")
                borders.append(element)

            element.set(qn("w:val"), "single")
            element.set(qn("w:sz"), size)
            element.set(qn("w:space"), "0")
            element.set(qn("w:color"), color)

    @staticmethod
    def _set_repeat_table_header(row):
        tr_pr = row._tr.get_or_add_trPr()
        header = OxmlElement("w:tblHeader")
        header.set(qn("w:val"), "true")
        tr_pr.append(header)

    @staticmethod
    def _set_keep_with_next(paragraph):
        p_pr = paragraph._p.get_or_add_pPr()
        keep_next = OxmlElement("w:keepNext")
        p_pr.append(keep_next)

    @staticmethod
    def _set_keep_together(paragraph):
        p_pr = paragraph._p.get_or_add_pPr()
        keep_lines = OxmlElement("w:keepLines")
        p_pr.append(keep_lines)

    @staticmethod
    def _set_table_cant_split(row):
        tr_pr = row._tr.get_or_add_trPr()
        cant_split = OxmlElement("w:cantSplit")
        tr_pr.append(cant_split)

    @staticmethod
    def _add_page_field(paragraph):
        run = paragraph.add_run()
        run.font.name = "Nirmala UI"
        run.font.size = Pt(8)
        run.font.color.rgb = RGBColor.from_string(
            WordExportService.GREY
        )

        field_begin = OxmlElement("w:fldChar")
        field_begin.set(qn("w:fldCharType"), "begin")

        instr = OxmlElement("w:instrText")
        instr.set(qn("xml:space"), "preserve")
        instr.text = " PAGE "

        field_sep = OxmlElement("w:fldChar")
        field_sep.set(qn("w:fldCharType"), "separate")

        field_text = OxmlElement("w:t")
        field_text.text = "1"

        field_end = OxmlElement("w:fldChar")
        field_end.set(qn("w:fldCharType"), "end")

        run._r.append(field_begin)
        run._r.append(instr)
        run._r.append(field_sep)
        run._r.append(field_text)
        run._r.append(field_end)

    @staticmethod
    def _add_bottom_border(paragraph, color, size="8", space="4"):
        p_pr = paragraph._p.get_or_add_pPr()
        p_bdr = OxmlElement("w:pBdr")
        bottom = OxmlElement("w:bottom")

        bottom.set(qn("w:val"), "single")
        bottom.set(qn("w:sz"), size)
        bottom.set(qn("w:space"), space)
        bottom.set(qn("w:color"), color)

        p_bdr.append(bottom)
        p_pr.append(p_bdr)

    @staticmethod
    def _add_horizontal_rule(document, color="B08D57", size="14"):
        paragraph = document.add_paragraph()
        paragraph.paragraph_format.space_before = Pt(2)
        paragraph.paragraph_format.space_after = Pt(12)

        p_pr = paragraph._p.get_or_add_pPr()
        p_bdr = OxmlElement("w:pBdr")
        bottom = OxmlElement("w:bottom")

        bottom.set(qn("w:val"), "single")
        bottom.set(qn("w:sz"), size)
        bottom.set(qn("w:space"), "1")
        bottom.set(qn("w:color"), color)

        p_bdr.append(bottom)
        p_pr.append(p_bdr)

        return paragraph

    @staticmethod
    def _add_page_break(document):
        document.add_page_break()

    @staticmethod
    def _set_document_background(section, color):
        # Word page background is not consistently honored by all viewers.
        # We therefore keep the document white and use designed elements.
        return

    # ------------------------------------------------------------------
    # INDEX / TOC
    # ------------------------------------------------------------------

    @staticmethod
    def _add_contents_page(document):
        heading = document.add_paragraph()
        heading.paragraph_format.space_before = Pt(20)
        heading.paragraph_format.space_after = Pt(4)

        run = heading.add_run("CONTENTS")
        run.bold = True
        run.font.name = "Nirmala UI"
        run.font.size = Pt(25)
        run.font.color.rgb = RGBColor.from_string(
            WordExportService.NAVY
        )

        WordExportService._add_bottom_border(
            heading,
            WordExportService.GOLD,
            size="12",
            space="5",
        )

        subtitle = document.add_paragraph()
        subtitle.paragraph_format.space_after = Pt(18)

        run = subtitle.add_run(
            "Category and author index"
        )
        run.font.name = "Nirmala UI"
        run.font.size = Pt(10)
        run.font.color.rgb = RGBColor.from_string(
            WordExportService.GREY
        )

        # Real Word TOC. Word calculates final page numbers.
        toc_paragraph = document.add_paragraph()
        toc_paragraph.paragraph_format.space_after = Pt(20)

        run = toc_paragraph.add_run()

        fld_begin = OxmlElement("w:fldChar")
        fld_begin.set(qn("w:fldCharType"), "begin")

        instr = OxmlElement("w:instrText")
        instr.set(qn("xml:space"), "preserve")
        instr.text = 'TOC \\o "1-2" \\h \\z \\u'

        fld_sep = OxmlElement("w:fldChar")
        fld_sep.set(qn("w:fldCharType"), "separate")

        placeholder = OxmlElement("w:t")
        placeholder.text = "Updating contents..."

        fld_end = OxmlElement("w:fldChar")
        fld_end.set(qn("w:fldCharType"), "end")

        run._r.append(fld_begin)
        run._r.append(instr)
        run._r.append(fld_sep)
        run._r.append(placeholder)
        run._r.append(fld_end)

        note = document.add_paragraph()
        note.paragraph_format.space_before = Pt(15)

        run = note.add_run(
            "Tip: In Microsoft Word, right-click the contents "
            "and choose “Update Field” → “Update entire table”."
        )
        run.italic = True
        run.font.name = "Nirmala UI"
        run.font.size = Pt(8.5)
        run.font.color.rgb = RGBColor.from_string(
            WordExportService.GREY
        )

    # ------------------------------------------------------------------
    # READING / NOTES PAGE
    # ------------------------------------------------------------------

    @staticmethod
    def _add_reading_page(document, category, category_number):
        """
        Dedicated blank writing page after every category.

        The page contains enough structure for a customer to manually
        write book names they have read. It is intentionally not a table
        tied to database data.
        """

        document.add_page_break()

        label = document.add_paragraph()
        label.alignment = WD_ALIGN_PARAGRAPH.CENTER
        label.paragraph_format.space_before = Pt(28)

        run = label.add_run(
            f"{category_number:02d}"
        )
        run.bold = True
        run.font.name = "Nirmala UI"
        run.font.size = Pt(11)
        run.font.color.rgb = RGBColor.from_string(
            WordExportService.GOLD
        )

        title = document.add_paragraph()
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        title.paragraph_format.space_after = Pt(6)

        run = title.add_run(
            "BOOKS I HAVE READ"
        )
        run.bold = True
        run.font.name = "Nirmala UI"
        run.font.size = Pt(24)
        run.font.color.rgb = RGBColor.from_string(
            WordExportService.NAVY
        )

        subtitle = document.add_paragraph()
        subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
        subtitle.paragraph_format.space_after = Pt(24)

        run = subtitle.add_run(category)
        run.font.name = "Nirmala UI"
        run.font.size = Pt(11)
        run.font.color.rgb = RGBColor.from_string(
            WordExportService.GREY
        )

        WordExportService._add_horizontal_rule(
            document,
            WordExportService.GOLD,
            size="8",
        )

        instruction = document.add_paragraph()
        instruction.alignment = WD_ALIGN_PARAGRAPH.CENTER
        instruction.paragraph_format.space_after = Pt(18)

        run = instruction.add_run(
            "Write down the books you have read from this category."
        )
        run.font.name = "Nirmala UI"
        run.font.size = Pt(9)
        run.font.color.rgb = RGBColor.from_string(
            WordExportService.GREY
        )

        # Writing area
        table = document.add_table(rows=1, cols=2)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.autofit = False

        table.columns[0].width = Inches(0.65)
        table.columns[1].width = Inches(6.75)

        header = table.rows[0]
        header.cells[0].width = Inches(0.65)
        header.cells[1].width = Inches(6.75)

        for i, text in enumerate(("NO.", "BOOK NAME")):
            cell = header.cells[i]
            WordExportService._set_cell_shading(
                cell,
                WordExportService.NAVY
            )
            WordExportService._set_cell_margins(
                cell,
                top=100,
                bottom=100,
                start=120,
                end=120,
            )

            paragraph = cell.paragraphs[0]
            paragraph.alignment = (
                WD_ALIGN_PARAGRAPH.CENTER
            )

            run = paragraph.add_run(text)
            run.bold = True
            run.font.name = "Nirmala UI"
            run.font.size = Pt(8)
            run.font.color.rgb = RGBColor.from_string(
                WordExportService.WHITE
            )

        # Enough writing lines for a physical customer catalogue.
        for number in range(1, 18):
            row = table.add_row()
            WordExportService._set_table_cant_split(row)

            for cell in row.cells:
                cell.vertical_alignment = (
                    WD_CELL_VERTICAL_ALIGNMENT.CENTER
                )
                WordExportService._set_cell_margins(
                    cell,
                    top=110,
                    bottom=110,
                    start=120,
                    end=120,
                )
                WordExportService._set_cell_border(
                    cell,
                    color=WordExportService.LIGHT_GREY,
                    size="4",
                )

            p = row.cells[0].paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_after = Pt(0)

            r = p.add_run(str(number))
            r.font.name = "Nirmala UI"
            r.font.size = Pt(8.5)
            r.font.color.rgb = RGBColor.from_string(
                WordExportService.GREY
            )

            # Leave book-name cell empty for handwriting.
            p2 = row.cells[1].paragraphs[0]
            p2.paragraph_format.space_after = Pt(0)

        # Small personal notes section
        notes = document.add_paragraph()
        notes.paragraph_format.space_before = Pt(18)
        notes.paragraph_format.space_after = Pt(4)

        run = notes.add_run("NOTES")
        run.bold = True
        run.font.name = "Nirmala UI"
        run.font.size = Pt(9)
        run.font.color.rgb = RGBColor.from_string(
            WordExportService.GOLD
        )

        for _ in range(2):
            p = document.add_paragraph(" ")
            WordExportService._add_bottom_border(
                p,
                WordExportService.LIGHT_GREY,
                size="4",
                space="1",
            )

    # ------------------------------------------------------------------
    # COVER
    # ------------------------------------------------------------------

    @staticmethod
    def _add_cover(document, total_books, category_count):
        section = document.sections[0]

        # Visual top block
        for _ in range(3):
            document.add_paragraph()

        top = document.add_paragraph()
        top.alignment = WD_ALIGN_PARAGRAPH.CENTER

        run = top.add_run("LIBRARY")
        run.bold = True
        run.font.name = "Nirmala UI"
        run.font.size = Pt(16)
        run.font.color.rgb = RGBColor.from_string(
            WordExportService.GOLD
        )

        title = document.add_paragraph()
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        title.paragraph_format.space_before = Pt(3)
        title.paragraph_format.space_after = Pt(4)

        run = title.add_run("BOOK CATALOGUE")
        run.bold = True
        run.font.name = "Nirmala UI"
        run.font.size = Pt(32)
        run.font.color.rgb = RGBColor.from_string(
            WordExportService.NAVY
        )

        WordExportService._add_horizontal_rule(
            document,
            WordExportService.GOLD,
            size="16",
        )

        subtitle = document.add_paragraph()
        subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
        subtitle.paragraph_format.space_after = Pt(24)

        run = subtitle.add_run("TAMIL BOOKS COLLECTION")
        run.bold = True
        run.font.name = "Nirmala UI"
        run.font.size = Pt(11)
        run.font.color.rgb = RGBColor.from_string(
            WordExportService.GREY
        )

        # Stats cards
        stats = document.add_table(rows=1, cols=2)
        stats.alignment = WD_TABLE_ALIGNMENT.CENTER
        stats.autofit = False

        stats.columns[0].width = Inches(3.3)
        stats.columns[1].width = Inches(3.3)

        values = [
            (f"{total_books:,}", "BOOKS"),
            (f"{category_count}", "CATEGORIES"),
        ]

        for i, (value, label) in enumerate(values):
            cell = stats.rows[0].cells[i]

            WordExportService._set_cell_shading(
                cell,
                WordExportService.PALE_GOLD
            )

            WordExportService._set_cell_border(
                cell,
                color=WordExportService.LIGHT_GOLD,
                size="8",
            )

            WordExportService._set_cell_margins(
                cell,
                top=220,
                bottom=220,
                start=180,
                end=180,
            )

            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER

            r = p.add_run(value)
            r.bold = True
            r.font.name = "Nirmala UI"
            r.font.size = Pt(22)
            r.font.color.rgb = RGBColor.from_string(
                WordExportService.NAVY
            )

            p2 = cell.add_paragraph()
            p2.alignment = WD_ALIGN_PARAGRAPH.CENTER

            r2 = p2.add_run(label)
            r2.bold = True
            r2.font.name = "Nirmala UI"
            r2.font.size = Pt(8)
            r2.font.color.rgb = RGBColor.from_string(
                WordExportService.GREY
            )

        for _ in range(8):
            document.add_paragraph()

        date_p = document.add_paragraph()
        date_p.alignment = WD_ALIGN_PARAGRAPH.CENTER

        r = date_p.add_run(
            datetime.now().strftime("%B %Y").upper()
        )
        r.font.name = "Nirmala UI"
        r.font.size = Pt(10)
        r.font.color.rgb = RGBColor.from_string(
            WordExportService.GREY
        )

        footer_text = document.add_paragraph()
        footer_text.alignment = WD_ALIGN_PARAGRAPH.CENTER
        footer_text.paragraph_format.space_before = Pt(10)

        r = footer_text.add_run(
            "LIBRARY COLLECTION"
        )
        r.bold = True
        r.font.name = "Nirmala UI"
        r.font.size = Pt(8)
        r.font.color.rgb = RGBColor.from_string(
            WordExportService.GOLD
        )

        document.add_page_break()

    # ------------------------------------------------------------------
    # MAIN EXPORT
    # ------------------------------------------------------------------

    @staticmethod
    async def generate_catalogue(books: list[dict]) -> BytesIO:
        # --------------------------------------------------------------
        # CATEGORY FILTER
        # --------------------------------------------------------------
        # Filter books to only include categories in CATEGORY_ORDER.
        filtered_books = []
        
        allowed_categories = {c.casefold() for c in WordExportService.CATEGORY_ORDER}

        for book in books:
            category = str(book.get("category") or "").strip().casefold()

            if category in allowed_categories:
                normalized_book = dict(book)
                normalized_book["category"] = category.title()
                filtered_books.append(normalized_book)

        books = filtered_books

        if not books:
            raise ValueError(
                "No books found with the requested categories."
            )

        document = Document()

        # Page setup
        for section in document.sections:
            section.top_margin = Inches(0.62)
            section.bottom_margin = Inches(0.62)
            section.left_margin = Inches(0.68)
            section.right_margin = Inches(0.68)
            section.header_distance = Inches(0.25)
            section.footer_distance = Inches(0.3)

        # Global styles
        styles = document.styles

        normal = styles["Normal"]
        normal.font.name = "Nirmala UI"
        normal.font.size = Pt(9.5)
        normal.font.color.rgb = RGBColor.from_string(
            WordExportService.CHARCOAL
        )

        heading1 = styles["Heading 1"]
        heading1.font.name = "Nirmala UI"
        heading1.font.size = Pt(18)
        heading1.font.bold = True
        heading1.font.color.rgb = RGBColor.from_string(
            WordExportService.NAVY
        )
        heading1.paragraph_format.space_before = Pt(8)
        heading1.paragraph_format.space_after = Pt(4)
        heading1.paragraph_format.keep_with_next = True

        heading2 = styles["Heading 2"]
        heading2.font.name = "Nirmala UI"
        heading2.font.size = Pt(13)
        heading2.font.bold = True
        heading2.font.color.rgb = RGBColor.from_string(
            WordExportService.GOLD
        )
        heading2.paragraph_format.space_before = Pt(13)
        heading2.paragraph_format.space_after = Pt(6)
        heading2.paragraph_format.keep_with_next = True

        # --------------------------------------------------------------
        # GROUP BOOKS
        # --------------------------------------------------------------

        grouped = defaultdict(lambda: defaultdict(list))

        for book in books:
            category = WordExportService._display_category(
                book.get("category") or "Uncategorized"
            )

            author = str(
                book.get("author") or "Unknown Author"
            ).strip()

            author = re.sub(r"\s+", " ", author)

            grouped[category][author].append(book)

        # Requested category order first.
        requested_map = {
            WordExportService._normalize_category(name): name
            for name in WordExportService.CATEGORY_ORDER
        }

        actual_categories = list(grouped.keys())

        ordered_categories = []

        for requested in WordExportService.CATEGORY_ORDER:
            key = WordExportService._normalize_category(requested)

            matches = [
                category
                for category in actual_categories
                if WordExportService._normalize_category(category) == key
            ]

            if matches:
                ordered_categories.extend(matches)

        # Any unexpected categories are retained rather than silently lost.
        remaining = [
            category
            for category in actual_categories
            if category not in ordered_categories
        ]

        remaining.sort(key=lambda x: x.casefold())
        ordered_categories.extend(remaining)

        # --------------------------------------------------------------
        # COVER
        # --------------------------------------------------------------

        WordExportService._add_cover(
            document,
            total_books=len(books),
            category_count=len(ordered_categories),
        )

        # --------------------------------------------------------------
        # CONTENTS
        # --------------------------------------------------------------

        WordExportService._add_contents_page(document)

        # --------------------------------------------------------------
        # REQUIRED BLANK PAGE AFTER INDEX
        # --------------------------------------------------------------

        document.add_page_break()

        # --------------------------------------------------------------
        # CATALOGUE
        # --------------------------------------------------------------

        for category_index, category in enumerate(
            ordered_categories,
            start=1,
        ):
            # Category page heading
            category_heading = document.add_paragraph(
                style="Heading 1"
            )
            category_heading.paragraph_format.space_before = Pt(8)
            category_heading.paragraph_format.space_after = Pt(4)

            run = category_heading.add_run(
                category.upper()
            )
            run.bold = True
            run.font.name = "Nirmala UI"
            run.font.size = Pt(18)
            run.font.color.rgb = RGBColor.from_string(
                WordExportService.NAVY
            )

            WordExportService._set_keep_with_next(
                category_heading
            )

            WordExportService._add_bottom_border(
                category_heading,
                WordExportService.GOLD,
                size="10",
                space="4",
            )

            category_book_count = sum(
                len(grouped[category][author])
                for author in grouped[category]
            )

            info = document.add_paragraph()
            info.paragraph_format.space_after = Pt(7)

            r = info.add_run(
                f"{category_book_count:,} books"
            )
            r.font.name = "Nirmala UI"
            r.font.size = Pt(8.5)
            r.font.color.rgb = RGBColor.from_string(
                WordExportService.GREY
            )

            # Authors
            authors = sorted(
                grouped[category].keys(),
                key=lambda x: x.casefold()
            )

            for author in authors:
                author_heading = document.add_paragraph(
                    style="Heading 2"
                )

                author_heading.paragraph_format.space_before = Pt(13)
                author_heading.paragraph_format.space_after = Pt(6)

                r = author_heading.add_run(author)
                r.bold = True
                r.font.name = "Nirmala UI"
                r.font.size = Pt(13)
                r.font.color.rgb = RGBColor.from_string(
                    WordExportService.GOLD
                )

                WordExportService._set_keep_with_next(
                    author_heading
                )

                author_books = sorted(
                    grouped[category][author],
                    key=WordExportService._serial_sort_key
                )

                # ------------------------------------------------------
                # AUTHOR BOOK LIST
                # ------------------------------------------------------

                table = document.add_table(
                    rows=1,
                    cols=3
                )

                table.alignment = WD_TABLE_ALIGNMENT.CENTER
                table.autofit = False

                # Fixed column widths:
                # Serial | Book Title | Price
                column_widths = [
                    Inches(0.75),
                    Inches(5.35),
                    Inches(1.15),
                ]

                for index, width in enumerate(column_widths):
                    table.columns[index].width = width

                header = table.rows[0]
                WordExportService._set_repeat_table_header(header)
                WordExportService._set_table_cant_split(header)

                header_values = [
                    "NO.",
                    "BOOK TITLE",
                    "PRICE",
                ]

                for index, value in enumerate(header_values):
                    cell = header.cells[index]
                    cell.width = column_widths[index]

                    WordExportService._set_cell_shading(
                        cell,
                        WordExportService.NAVY
                    )

                    WordExportService._set_cell_margins(
                        cell,
                        top=95,
                        bottom=95,
                        start=100,
                        end=100,
                    )

                    paragraph = cell.paragraphs[0]
                    paragraph.paragraph_format.space_after = Pt(0)

                    if index == 2:
                        paragraph.alignment = (
                            WD_ALIGN_PARAGRAPH.RIGHT
                        )
                    else:
                        paragraph.alignment = (
                            WD_ALIGN_PARAGRAPH.LEFT
                        )

                    r = paragraph.add_run(value)
                    r.bold = True
                    r.font.name = "Nirmala UI"
                    r.font.size = Pt(7.5)
                    r.font.color.rgb = RGBColor.from_string(
                        WordExportService.WHITE
                    )

                # Books
                for row_index, book in enumerate(author_books):
                    row = table.add_row()

                    WordExportService._set_table_cant_split(row)

                    serial = WordExportService._normalize_serial(
                        book.get("serial_number")
                    )

                    title = str(
                        book.get("title") or ""
                    ).strip()

                    price = str(
                        WordExportService._price_text(
                            book.get("price")
                        )
                    )

                    if row_index % 2 == 1:
                        fill = WordExportService.PALE_GOLD
                    else:
                        fill = WordExportService.WHITE

                    values = [
                        serial,
                        title,
                        price,
                    ]

                    for index, value in enumerate(values):
                        cell = row.cells[index]
                        cell.width = column_widths[index]

                        WordExportService._set_cell_shading(
                            cell,
                            fill
                        )

                        WordExportService._set_cell_margins(
                            cell,
                            top=80,
                            bottom=80,
                            start=100,
                            end=100,
                        )

                        WordExportService._set_cell_border(
                            cell,
                            color=WordExportService.LIGHT_GREY,
                            size="3",
                        )

                        cell.vertical_alignment = (
                            WD_CELL_VERTICAL_ALIGNMENT.CENTER
                        )

                        paragraph = cell.paragraphs[0]
                        paragraph.paragraph_format.space_before = Pt(0)
                        paragraph.paragraph_format.space_after = Pt(0)
                        paragraph.paragraph_format.line_spacing = 1.0

                        if index == 0:
                            paragraph.alignment = (
                                WD_ALIGN_PARAGRAPH.LEFT
                            )
                        elif index == 2:
                            paragraph.alignment = (
                                WD_ALIGN_PARAGRAPH.RIGHT
                            )
                        else:
                            paragraph.alignment = (
                                WD_ALIGN_PARAGRAPH.LEFT
                            )

                        r = paragraph.add_run(value)

                        r.font.name = "Nirmala UI"
                        r.font.size = Pt(9)

                        if index == 0:
                            r.bold = True
                            r.font.color.rgb = RGBColor.from_string(
                                WordExportService.NAVY
                            )

                        elif index == 2:
                            r.bold = True
                            r.font.color.rgb = RGBColor.from_string(
                                WordExportService.NAVY
                            )

                        else:
                            r.font.color.rgb = RGBColor.from_string(
                                WordExportService.CHARCOAL
                            )

                # Controlled spacing between authors.
                spacer = document.add_paragraph()
                spacer.paragraph_format.space_before = Pt(0)
                spacer.paragraph_format.space_after = Pt(2)

            # ----------------------------------------------------------
            # READING PAGE AFTER EVERY CATEGORY
            # ----------------------------------------------------------

            WordExportService._add_reading_page(
                document,
                category,
                category_index,
            )

            # The reading page already ends the category section.
            # Next category starts on a fresh page.
            if category_index < len(ordered_categories):
                document.add_page_break()

        # --------------------------------------------------------------
        # HEADER / FOOTER
        # --------------------------------------------------------------

        for section in document.sections:
            header = section.header
            hp = header.paragraphs[0]

            hp.alignment = WD_ALIGN_PARAGRAPH.LEFT
            hp.paragraph_format.space_after = Pt(2)

            r = hp.add_run("LIBRARY BOOK CATALOGUE")
            r.bold = True
            r.font.name = "Nirmala UI"
            r.font.size = Pt(7.5)
            r.font.color.rgb = RGBColor.from_string(
                WordExportService.GREY
            )

            WordExportService._add_bottom_border(
                hp,
                WordExportService.LIGHT_GREY,
                size="3",
                space="2",
            )

            footer = section.footer
            fp = footer.paragraphs[0]

            fp.alignment = WD_ALIGN_PARAGRAPH.CENTER

            r = fp.add_run(
                "OFFICIAL LIBRARY REGISTER   •   "
            )
            r.font.name = "Nirmala UI"
            r.font.size = Pt(7.5)
            r.font.color.rgb = RGBColor.from_string(
                WordExportService.GREY
            )

            WordExportService._add_page_field(fp)

        # --------------------------------------------------------------
        # UPDATE WORD FIELDS WHEN DOCUMENT OPENS
        # --------------------------------------------------------------

        settings = document.settings.element

        update_fields = settings.find(
            qn("w:updateFields")
        )

        if update_fields is None:
            update_fields = OxmlElement("w:updateFields")
            settings.append(update_fields)

        update_fields.set(qn("w:val"), "true")

        # --------------------------------------------------------------
        # SAVE
        # --------------------------------------------------------------

        output = BytesIO()
        document.save(output)
        output.seek(0)

        return output
