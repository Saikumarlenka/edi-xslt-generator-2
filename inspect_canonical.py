from lxml import etree

tree = etree.parse('reference-files/210/210_canonical_test.xml')
root = tree.getroot()
line_items = root.xpath('//*[local-name()="LineItem"]')
print(f"Total LineItems: {len(line_items)}")
for i, li in enumerate(line_items[:2]):
    print(f"--- LineItem {i} ---")
    for c in li:
        print(f"  <{etree.QName(c).localname}> {c.attrib}")

print("\n--- Checking Tariff and Commodity elements in InvoiceCanonicalSchema.xsd ---")
schema_tree = etree.parse('reference-files/210/InvoiceCanonicalSchema.xsd')
schema_root = schema_tree.getroot()
for el in schema_root.xpath('//*[@name="TariffReference" or @name="DescriptionMarksAndNumbers" or @name="CommodityCode2" or @name="TariffDistance"]'):
    print(f"Schema node: {el.tag} name={el.get('name')}")

