package templates

import (
	"bytes"
	"fmt"
	"strings"

	"github.com/russross/blackfriday"
)

const linebreak = "\n"

// ASCIIRenderer implements blackfriday.Renderer
var _ blackfriday.Renderer = &ASCIIRenderer{}

// ASCIIRenderer is a blackfriday.Renderer intended for rendering markdown
// documents as plain text, well suited for human reading on terminals.
type ASCIIRenderer struct {
	Indentation string

	listItemCount uint
	listLevel     uint
}

// NormalText gets a text chunk *after* the markdown syntax was already
// processed and does a final cleanup on things we don't expect here, like
// removing linebreaks on things that are not a paragraph break (auto unwrap).
func (r *ASCIIRenderer) NormalText(out *bytes.Buffer, text []byte) {
	raw := string(text)
	lines := strings.Split(raw, linebreak)
	for _, line := range lines {
		trimmed := strings.Trim(line, " \n\t")
		if len(trimmed) > 0 && trimmed[0] != '_' {
			out.WriteString(" ")
		}
		out.WriteString(trimmed)
	}
}

// List renders the start and end of a list.
func (r *ASCIIRenderer) List(out *bytes.Buffer, text func() bool, flags int) {
	r.listLevel++
	out.WriteString(linebreak)
	text()
	r.listLevel--
}

// ListItem renders list items and supports both ordered and unordered lists.
func (r *ASCIIRenderer) ListItem(out *bytes.Buffer, text []byte, flags int) {
	if flags&blackfriday.LIST_ITEM_BEGINNING_OF_LIST != 0 {
		r.listItemCount = 1
	} else {
		r.listItemCount++
	}
	indent := strings.Repeat(r.Indentation, int(r.listLevel))
	var bullet string
	if flags&blackfriday.LIST_TYPE_ORDERED != 0 {
		bullet += fmt.Sprintf("%d.", r.listItemCount)
	} else {
		bullet += "*"
	}
	out.WriteString(indent + bullet + " ")
	r.fw(out, text)
	out.WriteString(linebreak)
}

// Paragraph renders the start and end of a paragraph.
func (r *ASCIIRenderer) Paragraph(out *bytes.Buffer, text func() bool) {
	out.WriteString(linebreak)
	text()
	out.WriteString(linebreak)
}

// BlockCode renders a chunk of text that represents source code.
func (r *ASCIIRenderer) BlockCode(out *bytes.Buffer, text []byte, lang string) {
	out.WriteString(linebreak)
	lines := []string{}
	for _, line := range strings.Split(string(text), linebreak) {
		indented := r.Indentation + line
		lines = append(lines, indented)
	}
	out.WriteString(strings.Join(lines, linebreak))
}

// GetFlags TODO
func (r *ASCIIRenderer) GetFlags() int { return 0 }

// HRule TODO
func (r *ASCIIRenderer) HRule(out *bytes.Buffer) {
	out.WriteString(linebreak + "----------" + linebreak)
}

// LineBreak TODO
func (r *ASCIIRenderer) LineBreak(out *bytes.Buffer) { out.WriteString(linebreak) }

// TitleBlock TODO
func (r *ASCIIRenderer) TitleBlock(out *bytes.Buffer, text []byte) { r.fw(out, text) }

// Header TODO
func (r *ASCIIRenderer) Header(out *bytes.Buffer, text func() bool, level int, id string) { text() }

// BlockHtml TODO
func (r *ASCIIRenderer) BlockHtml(out *bytes.Buffer, text []byte) { r.fw(out, text) }

// BlockQuote TODO
func (r *ASCIIRenderer) BlockQuote(out *bytes.Buffer, text []byte) { r.fw(out, text) }

// TableRow TODO
func (r *ASCIIRenderer) TableRow(out *bytes.Buffer, text []byte) { r.fw(out, text) }

// TableHeaderCell TODO
func (r *ASCIIRenderer) TableHeaderCell(out *bytes.Buffer, text []byte, align int) { r.fw(out, text) }

// TableCell TODO
func (r *ASCIIRenderer) TableCell(out *bytes.Buffer, text []byte, align int) { r.fw(out, text) }

// Footnotes TODO
func (r *ASCIIRenderer) Footnotes(out *bytes.Buffer, text func() bool) { text() }

// FootnoteItem TODO
func (r *ASCIIRenderer) FootnoteItem(out *bytes.Buffer, name, text []byte, flags int) {
	r.fw(out, text)
}

// AutoLink TODO
func (r *ASCIIRenderer) AutoLink(out *bytes.Buffer, link []byte, kind int) { r.fw(out, link) }

// CodeSpan TODO
func (r *ASCIIRenderer) CodeSpan(out *bytes.Buffer, text []byte) { r.fw(out, text) }

// DoubleEmphasis TODO
func (r *ASCIIRenderer) DoubleEmphasis(out *bytes.Buffer, text []byte) { r.fw(out, text) }

// Emphasis TODO
func (r *ASCIIRenderer) Emphasis(out *bytes.Buffer, text []byte) { r.fw(out, text) }

// RawHtmlTag TODO
func (r *ASCIIRenderer) RawHtmlTag(out *bytes.Buffer, text []byte) { r.fw(out, text) }

// TripleEmphasis TODO
func (r *ASCIIRenderer) TripleEmphasis(out *bytes.Buffer, text []byte) { r.fw(out, text) }

// StrikeThrough TODO
func (r *ASCIIRenderer) StrikeThrough(out *bytes.Buffer, text []byte) { r.fw(out, text) }

// FootnoteRef TODO
func (r *ASCIIRenderer) FootnoteRef(out *bytes.Buffer, ref []byte, id int) { r.fw(out, ref) }

// Entity TODO
func (r *ASCIIRenderer) Entity(out *bytes.Buffer, entity []byte) { r.fw(out, entity) }

// Smartypants TODO
func (r *ASCIIRenderer) Smartypants(out *bytes.Buffer, text []byte) { r.fw(out, text) }

// DocumentHeader TODO
func (r *ASCIIRenderer) DocumentHeader(out *bytes.Buffer) {}

// DocumentFooter TODO
func (r *ASCIIRenderer) DocumentFooter(out *bytes.Buffer) {}

// TocHeaderWithAnchor TODO
func (r *ASCIIRenderer) TocHeaderWithAnchor(text []byte, level int, anchor string) {}

// TocHeader TODO
func (r *ASCIIRenderer) TocHeader(text []byte, level int) {}

// TocFinalize TODO
func (r *ASCIIRenderer) TocFinalize() {}

// Table TODO
func (r *ASCIIRenderer) Table(out *bytes.Buffer, header []byte, body []byte, columnData []int) {
	r.fw(out, header, body)
}

// Link TODO
func (r *ASCIIRenderer) Link(out *bytes.Buffer, link []byte, title []byte, content []byte) {
	out.WriteString(" ")
	r.fw(out, link)
}

// Image TODO
func (r *ASCIIRenderer) Image(out *bytes.Buffer, link []byte, title []byte, alt []byte) {
	r.fw(out, link)
}

func (r *ASCIIRenderer) fw(out *bytes.Buffer, text ...[]byte) {
	for _, t := range text {
		out.Write(t)
	}
}
