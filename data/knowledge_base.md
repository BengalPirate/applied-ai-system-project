# Music Knowledge Base

This corpus is the retrieval source for the MoodMatch Agent's RAG layer.
Each section is a self-contained passage. The retriever splits on the
"---" delimiter, so do not remove those.

---
title: lofi listener tendencies
tags: lofi, chill, focus, study, ambient, low-energy
Listeners who prefer lofi music typically value low energy levels (0.3-0.5),
soft acoustic textures, and continuous background presence. Strong adjacent
genres include ambient and jazz, especially for late-night study sessions.
For these users, prefer tracks with high acousticness (>0.6) and avoid
intense or rebellious moods even if energy levels happen to align.

---
title: pop crossover tips
tags: pop, happy, indie pop, dance, party
Pop fans often enjoy indie pop and tropical house when the mood is happy
and the tempo sits between 110 and 130 BPM. Latin pop and synthwave can
also satisfy upbeat valence preferences (>0.7) without genre exact match.
When recommending across genres for pop fans, prioritize valence and
danceability rather than purely energy.

---
title: rock and metal pairings
tags: rock, metal, intense, punk, gothic, high-energy
Rock listeners with high target energy (>0.85) usually accept punk and
metal as adjacent surfaces, especially when mood is intense or
rebellious. Gothic can satisfy "intense" mood requests when valence
is below 0.4. Avoid acoustic or peaceful tracks even when energy
roughly matches because the textural mismatch breaks immersion.

---
title: jazz and acoustic listening contexts
tags: jazz, relaxed, acoustic, blues, evening, dinner
Jazz fans typically appreciate blues, classical, and ambient tracks
when looking for relaxed or romantic atmospheres. The defining feature
is acousticness above 0.6 combined with valence between 0.5 and 0.8.
For "study" or "evening" contexts, energy below 0.45 is preferred.

---
title: edm and electronic boundaries
tags: edm, dubstep, dance, energetic, party, synth
EDM listeners reward genre adjacency to dubstep and synthwave when energy
exceeds 0.85 and acousticness is below 0.2. For party contexts,
danceability above 0.8 is the strongest single signal. Be cautious
with "intense" mood matches that lean rock or metal — these will feel
wrong even with similar energy because the timbre is different.

---
title: low-data genre fallback
tags: blues, country, gothic, classical, latin, niche
When a user requests a genre with only one song in the catalog (blues,
country, gothic, classical, latin, jazz fusion), confidence will be
low and the agent should expand the search to include adjacent genres
based on mood and energy. For sad blues, surface ambient or jazz with
low valence. For peaceful classical, surface ambient. The fallback
should be made transparent in the explanation.

---
title: discovery vs comfort tradeoff
tags: persona, discovery, comfort, filter bubble, diversity
The genre weight is the dominant lever for filter bubble vs discovery.
A genre weight near 2.0 produces a comfort experience: the user
sees mostly the same genre. A genre weight near 0.5 produces a
discovery experience: cross-genre matches surface even when imperfect.
The agent should reflect on diversity (number of distinct genres in
top-5) and lower the genre weight if all 5 results share a genre and
the user persona is "discovery".

---
title: workout and high-tempo guidance
tags: workout, gym, running, high-energy, tempo
For workout contexts, target energy should be at least 0.8 and tempo
above 120 BPM. EDM, pop, rock, and dubstep all serve this context.
Acoustic and ambient tracks should be down-weighted regardless of
genre match, because they break workout immersion.

---
title: study and focus guidance
tags: study, focus, library, concentration, low-distraction
For study contexts, prefer lofi, ambient, and instrumental jazz.
Energy should fall between 0.25 and 0.5. Tracks with valence
extremes (very happy or very sad) are distracting. Lyrics-heavy
genres like pop and rock are typically inappropriate.

---
title: mood-to-genre mapping
tags: mood, mapping, sad, happy, intense, chill, relaxed, peaceful
Sad mood maps best to blues, ambient, classical at low energy. Happy
mood maps to pop, indie pop, tropical house, latin. Intense mood maps
to rock, metal, punk, dubstep at high energy. Chill mood maps to lofi,
ambient, jazz at low to mid energy. Peaceful mood maps to ambient,
classical at very low energy. Romantic maps to r&b, jazz at mid energy.

---
title: artist over-exposure caution
tags: diversity, artist, repetition, fairness
When the top-5 contains the same artist more than twice, the agent
should flag low artist diversity and consider penalizing repeated
artists by 0.3 points to surface alternatives. This applies regardless
of persona because over-exposure undermines discovery and trust.
