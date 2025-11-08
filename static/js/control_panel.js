// Globals
var triggerKeys = ["name", "preset", "mode", "profile"];
var PROFILE_KEYS = 12;
var TRIGGER_PRESETS = 12;

function getValueForId(id) {
    return document.getElementById(id).value;
}

function getElement(id) {
    return document.getElementById(id);
}

function addEventListeners() {
    const forms = document.querySelectorAll("form");
    forms.forEach(form => {
      form.addEventListener("submit", function(e) {
        e.preventDefault();
        const button = this.querySelector("button");
        if (button) {
          button.style.backgroundColor = "#6F85D2";
        }
        setTimeout(() => { this.submit(); }, 500);
      });
    });

    fetchControlPanelData();
    fetchConfig();

    getElement("loading-message").style.display = 'none';
    getElement("message-box").style.display = 'none';

    getElement("connection-connection_type").addEventListener("click", function(event) {
        toggleSerialTelnet();
    });

    getElement("disconnect-button").addEventListener("click", function(event) {
      event.preventDefault();
      networkChange("/disconnect");
    });

    /*getElement("/set-hotspot-mode").addEventListener("click", function(event) {
      event.preventDefault();
      networkChange("/set-hotspot-mode");
    });
    
    getElement("sta-disconnect-button").addEventListener("click", function(event) {
      event.preventDefault();
      networkChange("/disconnect");
    });*/

    getElement("connect-button").addEventListener("click", function(event) {
      event.preventDefault();
      body = formToJson("wirelessClient")
      networkChange("/connect", body);
    });

    getElement("tink-submit").addEventListener("click", function(event) {
      event.preventDefault();
      updateConfig("tink");
    });

    getElement("tcp-submit").addEventListener("click", function(event) {
      event.preventDefault();
      updateConfig("tcpServer");
    });

    getElement("connection-submit").addEventListener("click", function(event) {
      event.preventDefault();
      updateConfig("switcher");
    });

    getElement("trigger-submit").addEventListener("click", function(event) {
        event.preventDefault();
        updateConfig("trigger-form");
    });

    getElement("add-trigger").addEventListener("click", function() {
        addTrigger("triggers", null);
    });
}

async function fetchConfig() {
    const request = new Request('/get-config');

    fetch(request)
    .then(response => {
        if(!response.ok) {
            throw new Error('Network response error');
        }
        return response.json();
    })
    .then(data => {
        masterKeys = ["tink", "tcpServer"];

        for(var i in masterKeys) {
            k = masterKeys[i];
            for(const [key, value] of Object.entries(data[k])) {
                if(k == "switchers") {
                    getElement(`${k}-${key}`)[0].value = value;
                }
                else {
                    getElement(`${k}-${key}`).value = value;
                }
            }
        }

        for(s in data.switchers) {
            if(data.switchers[s].enabled) {
                var i = 1;

                getElement("connection-enabled").value = data.switchers[s].enabled;
                getElement("connection-connection_type").value = data.switchers[s].connection_type;
                getElement("connection-type").value = data.switchers[s].type;
                getElement("connection-name").value = data.switchers[s].name;
                
                if(data.switchers[s].connection_type == "telnet") {
                    getElement("connection-hostname").value = data.switchers[s].connection.hostname;
                    getElement("connection-port").value = data.switchers[s].connection.port;
                    getElement("connection-username").value = data.switchers[s].connection.username;
                    getElement("connection-password").value = data.switchers[s].connection.password;
                    getElement("connection-init_string").value = data.switchers[s].connection.init_string;
                }
                else {
                    getElement("connection-txPin").value = data.switchers[s].connection.txPin;
                    getElement("connection-rxPin").value = data.switchers[s].connection.rxPin;
                    getElement("connection-uartId").value = data.switchers[s].connection.uartId;
                }

                for(const [key, value] of Object.entries(data.switchers[s].triggers)) {

                    // ugly way to only create if this exists
                    x = getElement(`trigger-${i}-name`);
                    if(x === null) {
                        addTrigger("triggers", i);
                    }
                    triggerKeys.forEach(function(key) {
                        getElement(`trigger-${i}-${key}`).value = value[key];
                    });
                    
                    ++i;
                }
            }
        }

        // Determine whether to show serial/telnet for the Extron, regardless
        // of whether the above works.
        toggleSerialTelnet();

    })
    .catch(error => {
        console.error(`Got this error ${error}`)
    });
}

async function networkChange(path, localBody) {
    const headers = new Headers();
    headers.append("Content-Type", "application/json");

    if(localBody != null) {
        b = localBody;
    }
    else {
        b = null;
    }

    const request = new Request(path, {
        method: "POST",
        body: b,
        headers: headers
    });

    fetch(request)
    .then(response => {
        if(!response.ok) {
            throw new error("Network response error");
        }
        return response.json;
    })
    .then(data => {
        if (data) {
            showMessageBox(data, "success");
        }
    })
    .catch(error => {
        console.error(error);
        showMessageBox(error, "error");
    })
}

async function fetchControlPanelData() {
    const request = new Request('/control-panel-data');

    fetch(request)
    .then(response => {
        if(!response.ok) {
            throw new Error('Network response error');
        }
        return response.json();
    })
    .then(data => {
        if(data) {
            // Populate hotspot/SSID data
            for(const [key, value] of Object.entries(data.ssid_info)) {
                getElement(key).innerHTML = value;
            }

            // Populate STA data
            for(const [key, value] of Object.entries(data.sta)) {
                getElement(key).innerHTML = value;
            }

            // Determine what displays on page
            getElement("disconnect-form").style.display = data.connected ? '' : 'none';
            getElement("sta-disconnect-form").style.display = data.connected ? '' : 'none';

            if(data.connected) {
                if(data.saved_connection_exists && data.sta.saved_ssid != null) {
                
                    if(data.ssid_info.saved_ssid == data.sta.sta_ssid) {
                        getElement("delete-connection-form").style.display = '';
                    }
                    else {
                        let owForm = getElement("overwrite-connection-form");
                        owForm.style.display = '';
                        // add in ssid and password
                        getElement("delete-connection-form").style.display = '';
                    }
                }
                else {
                    //getElement("save-connection-form").style.display = '';
                }
            }
            else {
                if(data.saved_connection_exists) {
                    getElement("delete-connection-form").style.display = '';
                }
            }
        }
    })
}

async function populateNetworks() {
    
    message = getElement("loading-message");
    message.style.display = '';

    const request = new Request('/scan_networks');

    fetch(request)
    .then(response => {
        if(!response.ok) {
        throw new Error('Network response error');
        }
        return response.json();
    })
    .then(data => {

        if (data) {
            // Data found, remove everything in list.
            selectList = getElement("network-select");
            selectList.innerHTML = "";
            
            data.forEach(function(ssid) {
                // Create new option for the SSID and add to list.
                selectList.appendChild(createOption(ssid, ssid));
            });
        }
    })
    .catch(error => {
        console.error("Could not load JSON data");
    })
    .finally(() => {
        message.style.display = 'none';
    });
}

async function updateConfig(formName) {

    path = "/save-config";
    const headers = new Headers();
    headers.append("Content-Type", "application/json");

    var body = "";
    switch(formName) {
        case("trigger-form"):
            body = triggersToJson();
            break;
        case("switcher"):
            body = formToSwitcherConfig();
            break;
        default:
            body = formToJson(formName);
            break;
    }

    const request = new Request(path, {
        method: "POST",
        body: body,
        headers: headers
    });

    fetch(request)
    .then(response => {
        if(!response.ok) {
            throw new Error('Network response error');
        }
        return response.json();
    })
    .then(data => {
        if(data.ok) {
            console.log(`Successfully saved ${formName}`);
            showMessageBox(`Successfully saved ${formName}`, "success");
        }
    })
    .catch(error => {
        console.error("Could not save configuration");
        showMessageBox(`Error: ${error}`, "error");
    })
    .finally(() => {

    });
}

function showMessageBox(message, type) {
    var m = getElement("message-box");
    m.style.display = '';
    m.classList = '';
    m.classList.add("alert");
    m.classList.add(type);

    getElement("message-text").innerHTML = message;
    
}

function addTrigger(t, num) {

    if(num === null) {
        num = document.getElementsByClassName("trigger-count").length;
        num = num == 0 ? 1 : Math.max(num, 1) + 1;
    }

    triggerRow = getElement(t);

    let name = document.createElement("input");
    name.id = `trigger-${num}-name`;
    name.className += "trigger-count";
    name.name = name.id;
    name.type = "text";

    triggerRow.appendChild(name);

    let triggerPreset = document.createElement("select");
    triggerPreset.id = `trigger-${num}-preset`;
    triggerPreset.name = triggerPreset.id;
    Array(TRIGGER_PRESETS).keys().forEach(i => {
        triggerPreset.append(createOption(i + 1, `Preset ${i + 1}`));
    });

    triggerRow.appendChild(triggerPreset);

    let triggerMode = document.createElement("select");
    triggerMode.id = `trigger-${num}-mode`;
    triggerMode.name = triggerMode.id;
    triggerMode.append(createOption("Remote", "Remote"));
    triggerMode.append(createOption("SVS", "SVS"));
    triggerRow.appendChild(triggerMode)

    let triggerProfile = document.createElement("select");
    triggerProfile.id = `trigger-${num}-profile`;
    triggerProfile.name = triggerProfile.id;
    Array(PROFILE_KEYS).keys().forEach(i => {
        triggerProfile.appendChild(createOption(i + 1, `Profile ${i + 1}`));
    });

    triggerRow.appendChild(triggerProfile);
}

function formToObject(formData) {
    var object = {};

    formData.forEach(function(value, key) {
        try {
            if(!isNaN(value)) {
                object[key] = JSON.parse(value);
            }
            else {
                object[key] = value;
            }
        }
        catch {
            console.log(`Failing on ${key} for ${value}`);
        }
    });

    return object;
}

function formToSwitcherConfig() {
    var object = {};

    object.enabled = JSON.parse(getValueForId("connection-enabled"));
    object.type = getValueForId("connection-type");
    object.name = getValueForId("connection-name");
    object.connection_type = getValueForId("connection-connection_type");
    object.connection = {};

    if(object.connection_type == "serial") {
        object.connection.txPin = JSON.parse(getValueForId(("connection-txPin")));
        object.connection.rxPin = JSON.parse(getValueForId(("connection-rxPin")));
        object.connection.uartId = JSON.parse(getValueForId(("connection-uartId")));
    }
    else {
        object.connection.hostname = getValueForId("connection-hostname");
        object.connection.port = JSON.parse(getValueForId("connection-port"));
        object.connection.username = getValueForId("connection-username");
        object.connection.password = getValueForId("connection-password");
        object.connection.init_string = getValueForId("connection-init_string");
    }

    var parent = {};
    parent.formName = "switcher";
    parent["switcher"] = object;
    return JSON.stringify(parent);
}

function formToJson(formName) {
    var object = {};
    form = getElement(formName);
    formData = new FormData(form);
    formData.forEach(function(value, key) {
        try {
            if(!isNaN(value)) {
                object[key] = JSON.parse(value);
            }
            else {
                object[key] = value;
            }
        }
        catch {
            console.log(`Failing on ${key} for ${value}`);
        }
    });

    var parent = {};
    parent.formName = formName;
    parent[formName] = object;
    return JSON.stringify(parent);
}

/*
    Dump all triggers to a JSON string object.
*/
function triggersToJson() {
    var array = [];

    for(var i = 1; i <= getElement("triggers").childNodes.length / triggerKeys.length; ++i) {
        
        var object = {};
        triggerKeys.forEach(function(key) {
            value = getValueForId(`trigger-${i}-${key}`);
            if(!isNaN(value)) {
                object[key] = JSON.parse(value);
            }
            else {
                object[key] = value;
            }
        });

        array.push(object);
    }

    var parent = {};
    parent.formName = "triggers";
    parent["triggers"] = array;

    return JSON.stringify(parent);
}

function createOption(value, text) {
    let x = document.createElement("option");
    x.value = value;
    x.text = text

    return x;
}

function toggle() {
    let en = getElement("tcpServer-enabled");
    let port = getElement("tcpServer-port");

    port.disabled = !(en.value === "true");
}

function toggleSerialTelnet() {
    var ec = getElement("connection-connection_type").value;

    getElement("extron-serial").style.display = (ec === "serial") ? '' : 'none';
    getElement("extron-telnet").style.display = (ec === "telnet") ? '' : 'none';
}