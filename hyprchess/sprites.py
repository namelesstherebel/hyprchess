"""Built-in pixel sprites. Each sheet stacks king, queen, rook, bishop, knight, pawn.

Two pixels per character row (half blocks). X = body, o = detail, . = empty.
"""

SHEETS = {
    8: """
        ...XX...
        ..XXXX..
        ...XX...
        .XXXXXX.
        .XXooXX.
        ..XXXX..
        .oooooo.
        .XXXXXX.

        ........
        o..oo..o
        X..XX..X
        XX.XX.XX
        .XXXXXX.
        ..XooX..
        .oooooo.
        .XXXXXX.

        ........
        .X.XX.X.
        .XXXXXX.
        .oooooo.
        ..XXXX..
        ..XXXX..
        .oooooo.
        .XXXXXX.

        ...XX...
        ...XX...
        ..XXoX..
        ..XoXX..
        ..XXXX..
        ...XX...
        .oooooo.
        .XXXXXX.

        ...X.X..
        ..XXXXX.
        .XoXXXo.
        XXXXXXo.
        XX.XXXo.
        ...XXXX.
        .oooooo.
        .XXXXXX.

        ........
        ........
        ..XXXX..
        ..XXXX..
        ...XX...
        ..XXXX..
        ..oooo..
        .XXXXXX.
    """,
    10: """
        ....XX....
        ..XXXXXX..
        ....XX....
        .XX.XX.XX.
        .XXXXXXXX.
        .XXXooXXX.
        ..XXXXXX..
        ..oooooo..
        .XXXXXXXX.
        .XXXXXXXX.

        ..........
        .o..oo..o.
        .X..XX..X.
        .XX.XX.XX.
        .XXXXXXXX.
        ..XooooX..
        ...XXXX...
        ..oooooo..
        .XXXXXXXX.
        .XXXXXXXX.

        ..........
        .XX.XX.XX.
        .XX.XX.XX.
        .XXXXXXXX.
        ..oooooo..
        ..XXXXXX..
        ..XXXXXX..
        ..oooooo..
        .XXXXXXXX.
        .XXXXXXXX.

        ....XX....
        ....XX....
        ...XXXX...
        ..XXXoXX..
        ..XXoXXX..
        ..XXXXXX..
        ...XXXX...
        ..oooooo..
        .XXXXXXXX.
        .XXXXXXXX.

        ....X.X...
        ...XXXXX..
        ..XoXXXXo.
        .XXXXXXXo.
        .XXX.XXXo.
        .X..XXXXX.
        ...XXXXX..
        ..oooooo..
        .XXXXXXXX.
        .XXXXXXXX.

        ..........
        ..........
        ...XXXX...
        ..XXXXXX..
        ..XXXXXX..
        ...XXXX...
        ..oooooo..
        ...XXXX...
        ..XXXXXX..
        ..XXXXXX..
    """,
    12: """
        .....XX.....
        ...XXXXXX...
        .....XX.....
        ..XX.XX.XX..
        .XXXXXXXXXX.
        .XXXXooXXXX.
        .XXXXooXXXX.
        ..XXXXXXXX..
        ...XXXXXX...
        ..oooooooo..
        .XXXXXXXXXX.
        .XXXXXXXXXX.

        ............
        .o..o..o..o.
        .X..X..X..X.
        .XX.XXXX.XX.
        .XXXXXXXXXX.
        ..XXXXXXXX..
        ..XooooooX..
        ...XXXXXX...
        ...XXXXXX...
        ..oooooooo..
        .XXXXXXXXXX.
        .XXXXXXXXXX.

        ............
        ..XX.XX.XX..
        ..XX.XX.XX..
        ..XXXXXXXX..
        ..oooooooo..
        ...XXXXXX...
        ...XXXXXX...
        ...XXXXXX...
        ...XXXXXX...
        ..oooooooo..
        .XXXXXXXXXX.
        .XXXXXXXXXX.

        .....XX.....
        .....XX.....
        ....XXXX....
        ...XXXoXX...
        ...XXoXXX...
        ...XoXXXX...
        ...XXXXXX...
        ....XXXX....
        ....XXXX....
        ..oooooooo..
        .XXXXXXXXXX.
        .XXXXXXXXXX.

        .....X.X....
        ....XXXXX...
        ...XXXXXXo..
        ..XXoXXXXXo.
        .XXXXXXXXXo.
        .XXXX.XXXXo.
        .XX..XXXXXo.
        ....XXXXXX..
        ...XXXXXXX..
        ..oooooooo..
        .XXXXXXXXXX.
        .XXXXXXXXXX.

        ............
        ............
        ............
        ....XXXX....
        ...XXXXXX...
        ...XXXXXX...
        ....XXXX....
        ...oooooo...
        ....XXXX....
        ...XXXXXX...
        ..XXXXXXXX..
        ..XXXXXXXX..
    """,
}
