start /b torpy_socks -p 9050 --hops 3
timeout 30
python __main__.py
