

payload = {'formName': {'name': 'Joe CrossPoint', 'connection_type': 'telnet', 'connection': {'username': '', 'init_string': 'W1CV', 'port': '23', 'password': '', 'hostname': '192.168.0.97'}, 'enabled': 'true', 'type': 'ExtronMavCp'}}

key = payload["formName"]
print(key)
data = []

if key == "triggers":
    data["switchers"][0][key] = payload[key]
elif key == "switcher":
    data["switchers"][0]["connection"] = payload[key]
    data["switchers"][0]["enabled"] = payload[key]["enabled"]
    data["switchers"][0]["type"] = payload[key]["type"]
    data["switchers"][0]["name"] = payload[key]["name"]
    data["switchers"][0]["connection_type"] = payload[key]["connection_type"]
else:
    data[key] = payload[key]

print(data)