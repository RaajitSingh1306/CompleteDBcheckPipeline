import re

def norm_name(name):
    if not name or str(name).lower() == "nan":
        return ""
    name = str(name).lower()
    name = re.sub(r'[^\w\s]', ' ', name)
    name = re.sub(r'\b(pvt ltd|private limited|ltd|inc|solutions|technologies)\b', '', name)
    return re.sub(r'\s+', ' ', name).strip()


def norm_web(url):
    if not url or str(url).lower() == "nan":
        return ""
    url = str(url).lower().strip()
    url = re.sub(r'https?://', '', url)
    url = re.sub(r'www\.', '', url)
    url = re.split(r'[/?#]', url)[0]
    return url.rstrip('/')
