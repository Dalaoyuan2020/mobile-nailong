# CAD prompt (English)

> Archived horizontal layout; superseded by the [current upright suitcase prompt](PROMPT_STAND_HANDLE.md). The board now rests against the front broad face of the upright case. Do not use the old orientation or wheelbase below for the current assembly.

You are a mechanical designer. Build an assemblable CAD model for "Mobile Nailong".

A 26-inch hard-shell suitcase lies on its largest face and acts as ballast plus a load cart. A 1500 × 500 × 8 mm KT standee is strapped on TOP of the suitcase (yellow cartoon dragon, front facing +X). Under the case: a flat drive plate, two rear driven wheels, two front casters.

Coordinates: origin at underside center of the case. +X forward, +Z up.
Case footprint 720 × 470 mm, shell 290 mm thick. Chassis plate 8 mm under the case, 50 mm margin. Wheel radius 50 mm. Track 400 mm. Wheelbase 540 mm. Standee base center is 40 mm aft of case-top center.

Do not stand the suitcase upright. Do not insert the board into the cavity. Do not make an A-frame. Do not use mecanum wheels. Do not make the board taller than 1500 mm above the case lid. Hide the telescopic handle. Put 8 × 1 kg ballast blocks on the inner floor. Strap the board with three ratchet straps around case + board.

Parts: case_26, chassis, wheel_drive ×2, wheel_caster ×2, standee, strap ×3, ballast ×8, imu_block 20×20×4 on the back of the board at 700 mm height, ESP32 box 80×50×30 on the inner rear wall.

Optimize in this order: lower CG, keep straps off the face art, chassis not proud of the case by more than 20 mm, wheels clear of the shell.

Deliver assembly, exploded view, envelope size, estimated CG with masses case 6 kg + ballast 8 kg + board 1.2 kg + chassis 2 kg. Also a 24-inch variant: 660 × 430 × 270, track 360, wheelbase 480.
