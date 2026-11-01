# EDI reference files

The supplied source files are organized by transaction. The backend automatically copies supplied references into `backend/data/references/` on startup when an active copy is absent. Use the Reference Library UI to replace an active reference; the archive here remains unchanged.

## EDI 210

| Project filename | Role |
|---|---|
| `210/210_mapping_matrix_Sonoco_RXO.docx` | Customer mapping matrix; authoritative business requirements |
| `210/210_standard_base.xsl` | Standard/baseline XSLT map |
| `210/InvoiceCanonicalSchema.xsd` | Canonical Invoice schema |
| `210/X12_00401_210.xsd` | BizTalk EDI X12 00401 210 schema |
| `210/210_canonical_test.xml` | Sample canonical Invoice XML |

The supplied 210 schema files are present but currently have namespace compatibility issues with the sample XML and map output. The validation report identifies these rather than claiming schema validation passed. The supplied test output also fails the local SE01 segment-count check.

## EDI 214

| Project filename | Role |
|---|---|
| `214/214_standard_base.xsl` | Standard/baseline 214 XSLT map |

Still needed for 214: mapping matrix DOCX, canonical Status XSD, EDI 214 XSD, and canonical Status test XML.
