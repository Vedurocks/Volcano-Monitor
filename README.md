# _*Volcano Eruption Monitor*_


> "Early warning system for volcanic activity using ultrasonic and vibration sensors"


**__ OVERVIEW __**

This project is a __low-cost volcanic monitoring system__ built with **Arduino**.
It uses an **__ultrasonic sensor__** to detect ground bulging and a **__vibration
sensor__** to detect seismic activity. When __both sensors trigger__, the system
activates a **__loud buzzer__** and **__LED alert__**.

> __"Simple, cheap, and effective - like a smoke detector for volcanoes."__


**__ FEATURES __**

[✓] **__Dual Sensor Confirmation__** — Both ultrasonic AND vibration must
    trigger for full alarm

[✓] **__Kill Switch__** — Manual override to silence false alarms

[✓] __Serial Control__ — Control via PC through USB

[✓] __Adjustable Thresholds__ — Change sensitivity from PC in real-time

[✓] __Real-time Data__ — Distance and vibration sent every 500ms


**__ HARDWARE REQUIRED __**

    Component                    Quantity    Cost (₹)
    ─────────────────────────────────────────────────
    **__Arduino Uno__**              1         ~400
    **__HC-SR04 Ultrasonic__**       1         ~80
    **__SW-180P Vibration__**          1         ~50
    **__5V Buzzer__**                1         ~30
    __LED (5mm)__                    1         ~5
    __220Ω Resistor__                2         ~2
    __Jumper Wires__                 Several   ~50
    ─────────────────────────────────────────────────
    
    > **__💰 Total: approximately ₹600-700__**


**__ PIN CONNECTIONS __**

    HC-SR04 Ultrasonic:
        VCC  → 5V
        GND  → GND
        TRIG → **__D2__** (Digital Output)
        ECHO → **__D4__** (Digital Input)

    Vibration Sensor (SW-180P):
        VCC     → 5V
        GND     → GND
        SIGNAL  → **__D5__** (Digital Input)

    LED:
        Anode (+) long leg  → **__D10__** (Digital Output)
        Cathode (-) short   → __220Ω → GND__

    Buzzer:
        Positive (+)  → **__D13__** (Digital Output)
        Negative (-)  → GND

    > __🔌 LED and Buzzer negative pins connect to GND through 220Ω resistors__


**__ SERIAL COMMANDS __**

    ▸ __`on`__         — Start the system
    ▸ __`off`__        — Stop the system
    ▸ __`kill`__       — **__🚨 Activate kill switch__**
    ▸ __`reset`__      — Reset kill switch
    ▸ __`456`__        — **__🧪 Force test alarm__**
    ▸ __`min ult X`__  — Set ultrasonic threshold (cm)
    ▸ __`min vib X`__  — Set vibration threshold (count)

    > __💡 Example: `min ult 15` sets distance alert to 15cm__


**__ DATA OUTPUT FORMAT __**

    Arduino sends **__CSV data__** every 500ms:

    distance,vibration,dist_alert,vib_alert,dual_alert,kill,sys,min_ultra,min_vib

    __Example:__
    45.67,2,DIST_OK,VIB_OK,DUAL_OK,KILL_OFF,SYS_ON,10.0,3

    __Field meanings:__

    📊 __45.67__      → **__Distance in cm__**
    📊 __2__          → **__Vibration count per second__**
    📊 __DIST_OK__    → **__Distance is normal__**
    📊 __VIB_OK__     → **__Vibration is normal__**
    📊 __DUAL_OK__    → **__No dual alert__**
    📊 __KILL_OFF__   → **__Kill switch inactive__**
    📊 __SYS_ON__     → **__System running__**
    📊 __10.0__       → **__Current ultrasonic threshold__**
    📊 __3__          → **__Current vibration threshold__**


**__ ALERT LOGIC __**

    ✅  Distance ≥ threshold  AND  Vibration < threshold   → __OK__
        LED 🔴 OFF  |  Buzzer 🔊 OFF

    ⚠️  Distance < threshold   AND  Vibration < threshold   → __Distance Only__
        LED 🔴 OFF  |  Buzzer 🔊 OFF

    ⚠️  Distance ≥ threshold  AND  Vibration ≥ threshold   → __Vibration Only__
        LED 🔴 OFF  |  Buzzer 🔊 OFF

    🚨  Distance < threshold   AND  Vibration ≥ threshold   → **__`DUAL ALERT`__**
        LED 🔴 **__ON__**  |  Buzzer 🔊 **__ON__**

    > __⚠️ Both sensors must agree before full alarm — prevents false alarms__


**__ INSTALLATION __**

    __Step 1: Upload Code__ 📝
        Open Arduino IDE → Select Board: Arduino Uno
        → Select COM Port → Upload code

    __Step 2: Open Serial Monitor__ 🔍
        Tools → Serial Monitor → Baud Rate: `9600`

    __Step 3: Send Command__ ▶️
        Type `on` → Press Enter


**__ TROUBLESHOOTING __**

    ❓ No distance reading?     → **__🔧 Check Trig/Echo wiring__**
    ❓ Buzzer too quiet?         → **__🔧 Use `tone()` instead of `digitalWrite()`__**
    ❓ Too many false alarms?    → **__🔧 Increase `min ult` or `min vib` values__**
    ❓ System not responding?    → **__🔧 Send `off` then `on` to reset__**


**__ LICENSE __**

    > __📜 "This project is open source. Use it, modify it, save lives with it."__


**__ Built with ❤️ for safety 🌋 __**
