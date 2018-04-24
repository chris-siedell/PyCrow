{
Part of a demonstration for using the Crow host.
April 2018
Chris Siedell

See "demo.py".
}

con
    _xinfreq = 5_000_000
    _clkmode = xtal1 + pll16x

obj 
    echo : "Echo.spin"

pub main

    echo.setPins(31, 30)
    echo.setBaudrate(115200)
    echo.setAddress(5)
    echo.setPort(100)
    echo.start
    

    

