# Hēlapidi — Design Decisions Log
*Living doc — update as decisions change. Last updated: July 10, 2026*

## Repo
https://github.com/Nanmin-Game-Studio/helapidi.git — branch `main`, 2 commits already in
(`Initial commit - Helapidi`, `Remove misnamed file`). Not starting from zero — build the
commit habit from here, not from `git init`.

## Core Loop
Multiplayer shooting game. Modes: 1v1, 2v2, 4v4.

## Game Client — EXISTS (`index.html`, ~2,560 lines)
A real, working single-file canvas engine, not a stub:
- `EventEmitter`, `ParticleSystem`, `WeaponSystem`, `AmmoCrateSystem`, `GrenadeSystem`,
  `LandmineSystem`, `HUDAnimator`, `InputManager`, `AudioManager`, `Player`, `Camera`,
  `NetworkManager`, `UIManager`, `GameLoop`
- `InputManager` already abstracts keyboard, gamepad, and touch behind one
  `isPressed(playerId, action)` interface — this is the exact interface the motion
  controller was always meant to plug into as a 4th input source
- Touch controls already built, but as a same-device split-screen 2P layout (both
  players' virtual buttons rendered together, left/right halves). Needs adjustment
  for remote play, where each device shows only its own controls
- `Player` already has an animation state machine (`_aState`, `_aFrame`) — currently
  driving colored-rectangle rendering, ready to swap for real sprites
- `NetworkManager` is scaffolded but not wired to a real server (`WS_URL` is empty —
  offline mode only). Real message protocol: `join`, `input`, `inputBatch` (batched
  raw input at tick rate), `state` (buffered snapshots), `event`, `ping`/`pong`, plus
  WebRTC signaling (`rtcOffer`/`rtcAnswer`/`rtcIce`) for peer-to-peer voice chat

## Characters — designed, not yet integrated as sprites
- **Kehi** (Kehibella) — Sri Lankan Blue Magpie-inspired, dual kris daggers, feather
  shotgun, slow-pace handgun, grenade/landmine
- **Kottu Rush** — chef-themed, chopper-rifle-ax, heat-plate spreader, spice-pistol, jetpack
- **Tuk-Tuk Aiya** — rifle, wrench melee, tuk-tuk sprint transformation, grenade/landmine
- Matches spec exactly: 2 male (Kottu Rush, Tuk-Tuk Aiya) + 1 female (Kehi)
- Animation sheets are discrete labeled poses (Idle, Jetpack Start/Fly/Loop/Finish, Gun
  Shoot, Knife Slash, Grenade Toss, Win/Defeat) — same shape as the `_aState`/`_aFrame`
  system already in `Player`. Likely needs frame-slicing, not a new animation tool —
  confirm this for real at step 4.

## World / UI Art — exists, not yet wired in
Main menu ("HĒLAPIDI" stone-arch title), game room (team-select lobby with VS mask +
enter-arena flow), Sigiriya-referencing ruin/platform level art, moonlit harbor level
art, Nanmin Game Studio logo.

## Aiming Mechanism — DECIDED: Zone Lock-On
- Reuses `lean_x` (already calibrated) as the zone selector: lean left / center / right
- Fire trigger reuses existing velocity-spike detection
- Auto-targets nearest enemy inside the selected zone
- RISK — zone flicker: needs hysteresis (lock holds until lean crosses well past boundary)
- RISK — mirrored zones: "lean left" must mean the same on-screen thing for both players
- DEPENDENCY — needs real networking (see below)

## Networking — CORRECTED DIRECTION
Earlier match-server draft (`match_server.py`) does NOT match this client's real
protocol and needs to be redone, not extended. Given `NetworkManager` already expects
raw `inputBatch` from clients and broadcasts `state` snapshots, the sane path is
**host-relay**: whoever creates the room runs the same local simulation the engine
already runs for local 2P, treated as authoritative; the server is a dumb router by
room — forward guests' `input`/`inputBatch` to the host, forward the host's `state` to
guests, relay `ping`/`pong` and WebRTC signaling untouched. Avoids duplicating the
already-working physics/collision logic server-side. Not built yet.

## Game Room (proposed flow; art mockup already exists for team-select screen)
1. Player connects, picks mode (1v1/2v2/4v4), quick-match or room code
2. Quick-match auto-splits teams for 2v2/4v4 — blind/random, no skill rating yet
3. Manual mode: host assigns Team A / Team B slots
4. Ready state = connected AND calibrated, not just connected
5. All ready → countdown → arena load → spawn by team side

## Roster Size, v1
Original "2 for v1" recommendation is largely moot — 3 characters are already fully
designed (Kehi, Kottu Rush, Tuk-Tuk Aiya). Fine to launch with what exists; just don't
design a 4th before the core loop actually works end to end.

## Mobile
- Confirmed: full native app on Play Store + App Store is the long-term target
- Existing touch controls are a real head start, but need reshaping from same-device
  split-screen to one-player-per-device
- Non-negotiable: all input sources (keyboard, touch, motion) write to the same
  `InputManager` state — no duplicated decision logic between them

## Sequence, as of this update
1. Git discipline from actual current state (in progress)
2. Networking protocol fix — host-relay server matching the real message types
3. Motion capture wired in as a 4th `InputManager` source
4. Character sprite integration (Kehi / Kottu Rush / Tuk-Tuk Aiya) into `_aState`;
   confirm animation tooling need here
5. Remaining screens — splash, loading, level select, shop, settings/profile

## Networking — Investigation Findings (git verified, commit f192ce2 live)
- Client ALREADY implements client-side prediction + reconciliation: `Player` buffers
  local input with sequence numbers (`_seq`, `_inputBuffer`), applies instantly, and on
  receiving authoritative `state` discards acknowledged inputs (`state.lastSeq`) and
  replays the rest. This is real, working netcode groundwork — not scaffolding.
- Client NEVER sends a `state` message — only consumes it (`_stateBuf`, drained each
  tick). Confirms original design intent was a real authoritative server, not host-relay.
  Host-relay is still the right call for a solo dev, but means writing NEW code on the
  host's client to serialize its own `Player` objects into `state` messages — not free.
- Zero room-creation/joining UI exists anywhere. Room = URL hash fragment, nothing else.
  Building real lobby UI stays step 5. Testing the protocol fix uses two tabs with a
  manually-typed matching hash — ugly and temporary on purpose.
- `_players` is built from `CONFIG.players.map(...)` — not hardcoded to 2, scales in
  principle. But camera modes (Static/Follow P1/Follow P2/Dynamic/Split) and HUD (two
  fixed panels) assume exactly 2 players. Real constraint, not a guess.
- SCOPE CUT: this networking pass targets 1v1 only. 2v2/4v4 wait for a separate camera +
  HUD rework — don't stack that problem on top of this one.
- CONFIG.network: tickRate 20Hz, reconnect up to 5x with exponential backoff (already
  built and working at the transport level).

## Next Build (in progress)
Python relay server matching real message types: `join`→assign `playerId`,
`input`/`inputBatch` from guest→host, `state` from host→guest, `ping`/`pong`. Plus new
host-side client code to serialize `Player` state and broadcast it. 1v1 only.

## Networking — 1v1 Host-Relay: BUILT AND VERIFIED
`relay_server.py` (Python/websockets) + client patch to `index.html`, tested end to end
with two real headless-browser instances against a real running server (not asserted):
- Host joins first → assigned `p1`. Guest joins second → assigned `p2`. Room full at 2.
- Guest's `inputBatch` relayed to host; host applies it to its local (non-local) p2 via
  the existing `applyInput()` — no new physics code, reused what was already there.
- Host broadcasts `state` (both players, matching the exact schema the client already
  expected: id/x/y/vx/vy/health/ammo/jetpack/facing/lastSeq) at `CONFIG.network.tickRate`.
- Verified: guest moves → host's independent simulation lands on the exact same
  coordinates as the guest's own prediction. Host moves → guest's smoothed view
  converges to the exact same coordinates as the host's own prediction. Both directions
  confirmed, not just one.

### Known limits of this pass — not yet done, know before relying on this
- Tested on localhost only — real internet latency/packet loss/jitter not exercised
- No lobby UI — room = manually-typed URL hash, on purpose, per the sequencing decision
- No reconnect-mid-match testing — transport reconnect exists (already built), whether
  game state recovers cleanly after a host or guest reconnects is unverified
- Server isn't deployed anywhere — runs on whoever starts `python3 relay_server.py`;
  actually hosting it somewhere both players can reach is a separate remaining task
- 2v2/4v4 still deliberately out of scope (camera/HUD rework required first)

## Single-Perspective HUD + Pause Menu — BUILT AND VERIFIED
- Camera: new 'self' mode follows whichever player `isLocal` is (not hardcoded p1/p2),
  auto-activates the moment a network playerId is assigned.
- HUD: panel 1 always shows the LOCAL player's stats regardless of p1/p2 id (tested:
  correct on both host and guest, not just array-index-0). Panel 2 hidden entirely —
  no permanent enemy stat panel.
- Enemy health: floating bar above an enemy's head, appears on `player:hit`, fades over
  ~4s. Tracked in `UIManager._enemyHitTimes` (Map: playerId -> last hit timestamp).
- Pause menu: Escape toggles a Resume/Quit overlay; gates the update loop via
  `GameLoop._paused`. Quit currently reloads the page (no title/menu screen exists yet
  to return to — real destination is later, once that screen is built).
- Modes confirmed by user: Solo (1v7), Duos (2v2, selectable 2/3/4 teams), Squads (4v4)
  — all within a fixed 8-player arena. Team-grouping logic on top of a shared room size,
  not three separate systems. NOT built yet — this session was 1v1 HUD/camera only.

## Bug Fixes — Round-Over Sync, Coin Sync, Weapon Switch, Dead UI (VERIFIED)
- **Round-over/wins desync (root cause found):** both host and guest ran
  `_checkRoundOver()` independently against their own (differently-timed) view of the
  other player's health, so they could reach different conclusions at different
  moments — matching the screenshot evidence (different wins count, overlay on one
  screen not the other). Fixed: host-authoritative — only host decides, broadcasts via
  a new `sendEvent('roundEnd',{winner,s1,s2})`, guest applies it directly. Server needed
  a new generic `event` relay case to support this (added).
- **Coin collection desync:** same root cause, different system — both sides ran their
  own collision check against both players. Fixed the same way: host-only decides,
  broadcasts `{index,total}`, guest applies without re-deciding.
- **Weapon switch (1-5 keys) was hardcoded to always target `p1`** regardless of who
  pressed it — a leftover from local same-device 2P. Fixed to target whichever player
  is actually local on that client.
- **Removed a pre-existing always-on name-tag + health bar** drawn above every player's
  head every frame (separate from the hit-triggered one already built) — this is what
  was actually causing "the health bar never goes away."
- **Removed the camera mode selector panel** (Static/Follow P1/Follow P2/Dynamic/Split)
  entirely — dead UI now that camera auto-follows the local player.

## Weapon System Redesign — PROPOSED, NOT BUILT
Mini Militia-referenced spec: 3 inventory slots total (2 weapons + 1 explosive slot
holding either 3 grenades or 2 landmines, not both). Start with pistol + character
melee. New weapons via random treasure-box spawns (same category as fuel/ammo pickups);
opening one has an unlock delay during which the player can't fire — a deliberate
vulnerability window for balance. Swapping = drop current, pick up new. Real,
well-specified idea — sequenced after the current bug-fix pass, not part of it.

## Coin Collection — Corrected to Per-Player (was wrongly shared)
Previous fix solved the sync *race* but kept coins as one shared total — wrong data
model, confirmed by your screenshot showing identical "2/20" on both screens. Reworked:
- `coinsCollected` is now a property on each `Player`, not one shared counter.
- Collision check credits whichever specific player touched the coin.
- Host still authoritative for detection (unchanged, still avoids the original race),
  but now broadcasts `{index, playerId, count}` so the guest credits the right player.
- HUD shows only the local player's own count — verified independently correct on both
  screens (not coincidentally equal).
- Resets per-player each round, alongside the existing coin respawn.

## Weapon System Rework — Data Shape (write-down before implementation)
Branch: `weaponSystem`. Replaces the current model where every player permanently owns
all 5 weapon types with their own ammo pools (`activeWeapon` = which one is "on
screen"). New shape, per player:

```js
weaponSlots: [
  { type:'pistol', mag:8, reserve:24 },   // slot 0 — starting weapon, every player
  { type:'melee' }                         // slot 1 — character melee, no ammo, always owned
],
activeSlotIndex: 0,   // which of weaponSlots[0/1] is currently equipped
explosive: { type:'grenade', count:3 }     // OR {type:'landmine', count:2} — mutually exclusive, one slot
```

Key differences from today: a slot can be **empty or occupied by a specific acquired
weapon**, not "always all 5, pick which is active." Picking up a new weapon from a
treasure box fills an empty slot, or — if both are full — forces a drop-and-replace on
whichever slot the player chooses. The explosive slot holds ONE type at a time (3
grenades OR 2 landmines), never both.

## Staged Build Plan (per council recommendation — one piece at a time, 1v1 only)
1. **Inventory model + swap mechanics** (this session) — can a player hold 2 weapons +
   1 explosive and switch/drop/equip correctly, tested with a debug grant method, no
   treasure boxes yet.
2. Treasure-box entities: spawn, closed/opening/looted states, random placement —
   host-authoritative from the first line, not retrofitted after a sync bug (this
   project has hit that exact mistake twice already: round-over, then coins).
3. Unlock-vulnerability window (can't fire while opening a box) — last, as a refinement
   once 1 and 2 are solid.

Not touching Solo/Duos/Squads until this works in 1v1 first, same discipline as
networking and the HUD rework.

## Weapon System Rework — Piece 1 Done: Inventory Model (VERIFIED)
- `WeaponSystem` rebuilt around `weaponSlots` (2, starts pistol + melee) and a single
  `explosive` slot (starts grenade×3). `activeWeapon` kept as a derived/mirrored
  property so the ~25 existing call sites (HUD, shoot/throw logic, damage calc) kept
  working unmodified — did not touch those, on purpose, to limit blast radius.
- Added `melee` to `CONFIG.weapons` (character-specific melee is still generic/placeholder
  until character integration happens — real per-character melee is a later dependency).
- `equipWeapon(type)` — fills an empty slot if one exists, otherwise replaces whichever
  slot is currently active; returns what got dropped. Both slots start populated
  (pistol + melee), so in practice v1 always replaces-the-active-slot — refine this to
  genuine slot choice once drop-to-ground exists.
- `useExplosive()` — grenade/landmine now come from one shared slot, not the old
  always-available separate weapon types. Fixed a real double-decrement bug this
  surfaced: `LandmineSystem.plant()` used to consume ammo itself; now the caller
  consumes via `useExplosive()` before calling `plant()`, matching the grenade pattern.
- HUD rebuilt: 3 slots (2 weapons + explosive with an "E" marker) instead of 5.
- TEMP/DEBUG ONLY: pressing `T` grants a random weapon, to test `equipWeapon()` without
  a treasure-box system existing yet. Remove this key binding once real pickups exist.

### Explicitly not done yet (pieces 2 and 3, per the staged plan)
- Treasure-box entities (spawn, closed/opening/looted states, random placement) — not
  built. Must be host-authoritative from line one this time, not retrofitted.
- Unlock-vulnerability window (can't fire while opening a box) — not built, depends on
  treasure boxes existing first.
- Dropped weapons don't spawn on the ground yet — `equipWeapon` returns what was
  dropped, but nothing currently does anything with that value.
- Real melee combat (an actual attack, not just an equippable slot) — not built.
- None of this has been tested over the network yet — this session was local-only,
  matching "test the inventory model in isolation first."

## Weapon System Rework — Status Update (branch: weaponSystem)
**Piece 1 (inventory model) was already built** earlier in this session — found, not
remembered cleanly, then re-verified for real (pressed the debug key twice, confirmed
correct slot-fill and active-slot-replace behavior) before trusting it.

**Piece 2 (treasure boxes) — BUILT AND VERIFIED THIS SESSION:**
- `TreasureBoxSystem`, modeled on the existing `AmmoCrateSystem` pattern (random spawn
  on wood platforms, timer-gated, proximity-triggered).
- Host-authoritative from the start (per the council's own recommendation) — only the
  host decides spawn/unlock/loot; guest mirrors via 4 new event types (`boxSpawned`,
  `boxUnlockStart`, `boxUnlockCancel`, `boxLooted`).
- Unlock takes `CONFIG.treasureBox.unlockTime` (2.5s default) standing near the box;
  walking away cancels progress. Blocks firing for the duration via `player.isUnlocking`
  — the deliberate vulnerability window from the original spec.
- On completion, grants a random weapon via the existing `equipWeapon()` — no new
  pickup-application logic needed, reused what Piece 1 already built.
- Debug 'T' key removed now that real pickups exist, per its own comment.
- Config: `treasureBox: { spawnInterval:22, maxBoxes:2, radius:36, unlockTime:2.5,
  pool:['pistol','shotgun','smg'] }`

**Known cleanup, not urgent:** `CONFIG.weapons` still has leftover `slot:1`-`slot:5`
fields from the old 5-weapon model. Nothing reads them anymore (confirmed) — cosmetic
debt, not a bug.

**Not built yet:** Piece 3 (explicit visual/audio telegraphing of the vulnerability
window beyond the progress bar), drop-to-ground for the weapon you swap away, and
character-specific melee weapons (still generic — real integration waits on the actual
Kehi/Kottu Rush/Tuk-Tuk Aiya sprites, sequenced later per the existing roadmap).

## Mobile Optimization Pass — VERIFIED (branch: weaponSystem)
Tested on real device emulation (Playwright + Pixel 5 profile, both orientations),
not just read from code — found two real bugs and one real gap:

- **Touch had no movement input at all.** `isPressed()` checked keyboard → gamepad →
  touch, but the touch overlay only ever set jump/shoot/jetpack/reload. On an actual
  phone with no keyboard, movement was impossible. Added `◀`/`▶` touch buttons;
  confirmed on-device that holding one actually moves the local player (x: 400→592
  over 600ms).
- **Touch overlay was still building one control set per player** (leftover from the
  same-device split-screen era) — would have shown a second, non-functional control set
  belonging to the other player on a real phone. Rewrote to build exactly one overlay,
  for whichever player the network actually assigns as local (`setActiveTouchPlayer`,
  called from the existing `network:playerId` handler). Falls back to `p1` for
  offline/local testing.
- **Landscape-only game, no portrait handling** — canvas scaling itself was already
  correct (aspect-ratio-preserving scale-to-fit), but a portrait phone shrank the game
  into a thin horizontal strip with large empty margins. Added a rotate-to-landscape
  prompt, gated to touch devices only (confirmed a narrow desktop window does NOT
  trigger it) so it never falsely fires for a resized desktop browser.

Not addressed this pass: on-screen weapon-slot switching for touch (currently still
keyboard-only via 1/2 keys) — worth a follow-up once this lands.
