{
Part of a demonstration for using the Crow host.
April 2018
Chris Siedell
http://www.siedell.com/projects/Crow/

See "demo.py".
}

con
    _xinfreq = 5_000_000
    _clkmode = xtal1 + pll16x

obj 
    'peekpoke : "PeekPoke.spin"
    echo : "PropCR-BD.spin"

pub main

    echo.setPins(31, 30)
    echo.setBaudrate(115200)
    echo.setAddress(5)
    echo.setUserPort(100)
    echo.start
    
    'peekpoke.setParams(31, 30, 230400, 6)
    'peekpoke.new

    'uncomment to turn on led on pin 27 (e.g. flip module)
'    dira[27] := 1
'    outa[27] := 1
'    repeat
'        waitcnt(0)
    

