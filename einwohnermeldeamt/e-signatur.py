from lxml import etree
from signxml import XMLSigner, XMLVerifier

data_to_sign = """<Test heute="2024-12-11">:-)</Test>"""

cert = open("cert.pem").read()
key = open("privkey.pem").read()

root = etree.fromstring(data_to_sign)

signed_root = XMLSigner().sign(root, cert=cert, key=key)
signed_root
with open("signed.xml", "wb") as datei:
    datei.write(etree.tostring(signed_root))
#verified_data = XMLVerfifier().verify(signed__root).signed_xml

with open("signed.xml") as signierteDatei:
    signed = etree.parse(signierteDatei)
XMLVerifier().verify(signed, x509_cert=cert).signed_xml



#XHTML benutzen statt fPDF