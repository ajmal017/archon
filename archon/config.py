import toml

def toml_file(fs):
    try:
        with open(fs, "r") as f:
            r = f.read() 
            return r           
    except Exception as e:
        raise Exception("toml file not found %s"%str(fs))

def parse_toml(filename):
    toml_string = toml_file(filename)
    parsed_toml = toml.loads(toml_string)
    return parsed_toml

