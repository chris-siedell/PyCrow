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

    echo.setParams(31, 30, 115200, 5, 100)
    echo.Start(0)
    
    'peekpoke.setParams(31, 30, 230400, 6)
    'peekpoke.new

    'uncomment to turn on led on pin 27 (e.g. flip module)
'    dira[27] := 1
'    outa[27] := 1
'    repeat
'        waitcnt(0)
    

