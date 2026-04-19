import sys
try:
    import pypdf
    reader = pypdf.PdfReader('c:\\Users\\leonh\\LRZ Sync+Share\\Additive Fertigung\\EBM-Strategy-Software\\1-s2.0-S2214860417302439-main.pdf')
    text = ''
    for i in range(min(5, len(reader.pages))):
        text += reader.pages[i].extract_text()
    with open('_temp_pdf.txt', 'w', encoding='utf-8') as f:
        f.write(text)
    print('Extract success')
except Exception as e:
    print('Failed:', str(e))
