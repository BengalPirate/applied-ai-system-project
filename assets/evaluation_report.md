# MoodMatch Agent -- Evaluation Report
_Generated 2026-04-27T07:12:54+00:00_

## Summary
- cases run: **6**
- cases fully passing: **6 / 6**
- assertions passed: **20 / 20** (100.0%)
- average confidence: **0.851** (high)
- median confidence:  **0.861**
- min confidence:     **0.701**
- average iterations: **1.00** (max=2)

## Per-case breakdown

### High-energy pop fan (default persona)
- user_prefs: `{"genre": "pop", "mood": "happy", "energy": 0.85, "valence": 0.85}`
- persona requested: `default` -> selected `default`
- iterations: 1
- confidence: 0.876 (high)
- top recommendations:
  1. Sunrise City (Neon Echo) [pop/happy] score=4.95
  2. Gym Hero (Max Pulse) [pop/intense] score=3.84
  3. Summer Vibes (Beach Party) [tropical house/happy] score=2.88
- assertions:
  - [PASS] k>=5 -- Should return at least 5 recommendations.
  - [PASS] top_genre==pop -- Top recommendation should be in genre 'pop'.
  - [PASS] confidence>=0.55 -- Overall confidence should be at least 0.55.
### Lofi study session (study persona auto-routes)
- user_prefs: `{"genre": "lofi", "mood": "chill", "energy": 0.4, "likes_acoustic": true}`
- persona requested: `(auto)` -> selected `study`
- iterations: 1
- confidence: 0.701 (medium)
- top recommendations:
  1. Midnight Coding (LoRoom) [lofi/chill] score=5.46
  2. Library Rain (Paper Lanterns) [lofi/chill] score=5.40
  3. Spacewalk Thoughts (Orbit Bloom) [ambient/chill] score=4.26
- assertions:
  - [PASS] k>=5 -- Should return at least 5 recommendations.
  - [PASS] persona==study -- Routed persona should be 'study'.
  - [PASS] top_genre==lofi -- Top recommendation should be in genre 'lofi'.
  - [PASS] confidence>=0.55 -- Overall confidence should be at least 0.55.
### Workout EDM (workout persona auto-routes, enforces energy floor)
- user_prefs: `{"genre": "edm", "mood": "energetic", "energy": 0.95, "likes_acoustic": false, "valence": 0.75}`
- persona requested: `(auto)` -> selected `workout`
- iterations: 1
- confidence: 0.814 (high)
- top recommendations:
  1. Digital Dreams (Cyber Flux) [edm/energetic] score=4.33
  2. Latin Fire (Salsa Kings) [latin/energetic] score=3.40
  3. Bass Drop City (DJ Voltage) [dubstep/energetic] score=3.23
- assertions:
  - [PASS] k>=5 -- Should return at least 5 recommendations.
  - [PASS] persona==workout -- Routed persona should be 'workout'.
  - [PASS] all_energy>=0.7 -- Every recommendation should have energy >= 0.7.
  - [PASS] confidence>=0.55 -- Overall confidence should be at least 0.55.
### Discovery mode pop fan (broaden recommendations)
- user_prefs: `{"genre": "pop", "mood": "happy", "energy": 0.8, "valence": 0.8}`
- persona requested: `(auto)` -> selected `discovery`
- iterations: 1
- confidence: 0.846 (high)
- top recommendations:
  1. Sunrise City (Neon Echo) [pop/happy] score=4.43
  2. Rooftop Lights (Indigo Parade) [indie pop/happy] score=3.73
  3. Summer Vibes (Beach Party) [tropical house/happy] score=3.70
- assertions:
  - [PASS] k>=5 -- Should return at least 5 recommendations.
  - [PASS] persona==discovery -- Routed persona should be 'discovery'.
  - [PASS] distinct_genres>=3 -- Top results should span at least 3 distinct genres.
### Niche blues sad mood (low-data fallback)
- user_prefs: `{"genre": "blues", "mood": "sad", "energy": 0.3}`
- persona requested: `default` -> selected `default`
- iterations: 1
- confidence: 0.936 (high)
- top recommendations:
  1. Rainy Day Blues (Delta Soul) [blues/sad] score=4.48
  2. Spacewalk Thoughts (Orbit Bloom) [ambient/chill] score=1.47
  3. Library Rain (Paper Lanterns) [lofi/chill] score=1.42
- assertions:
  - [PASS] k>=5 -- Should return at least 5 recommendations.
  - [PASS] top_genre==blues -- Top recommendation should be in genre 'blues'.
  - [PASS] distinct_genres>=3 -- Top results should span at least 3 distinct genres.
### Comfort persona for rock fan (narrow on rock)
- user_prefs: `{"genre": "rock", "mood": "intense", "energy": 0.9, "likes_acoustic": false}`
- persona requested: `comfort` -> selected `comfort`
- iterations: 1
- confidence: 0.935 (high)
- top recommendations:
  1. Storm Runner (Voltline) [rock/intense] score=6.19
  2. Gym Hero (Max Pulse) [pop/intense] score=3.16
  3. Thunderstruck Anthem (Iron Thunder) [metal/intense] score=3.11
- assertions:
  - [PASS] k>=5 -- Should return at least 5 recommendations.
  - [PASS] top_genre==rock -- Top recommendation should be in genre 'rock'.
  - [PASS] confidence>=0.55 -- Overall confidence should be at least 0.55.
