# Probe results

Model `prisma-v3.0` for speech-to-text, `timbre-v2.5` voice `Nalini` for the caller. Audio is two spoken groups of five digits with a pause of known length between them, 16 kHz.

## Gates

| Gate | Question | Result |
|---|---|---|
| 1 | Key works for REST STT, realtime STT and TTS | PASS |
| 2 | Streamed digits correct in at least 8 of 10 calls | PASS (10 of 10) |
| 3 | First group's text arrives within 0.6 s of the pause starting (median) | PASS (median 0.39 s) |
| 4 | `commit` frame closes the utterance early | PASS |
| 5 | Two streams can be open at once | PASS |

Gates 1 to 3 decide whether the design stands. Gates 4 and 5 only choose between options.

## REST transcription of the whole call

| Format | Transcript | Digits heard | Correct |
|---|---|---|---|
| verbatim | नौ, आठ, सात, छह, पाँच, चार, तीन, दो, एक, शून्य। | 9876543210 | yes |
| codemix | नौ, आठ, सात, छह, पाँच, चार, तीन, दो, एक, शून्य। | 9876543210 | yes |
| transcribe | 9876543210 | 9876543210 | yes |

## Realtime survey: one call, 0.8 s pause, every window and format

| Window ms | Format | Segments | Digits heard | Correct | Text after pause (s) |
|---|---|---|---|---|---|
| 200 | verbatim | नौ आठ सात छह पाँच। / चार तीन दो एक शून्य। | 9876543210 | yes | 0.396 |
| 200 | codemix | नौ, आठ, सात, छः, पाँच। / चार, तीन, दो, एक, शून्य। | 9876543210 | yes | 0.41 |
| 200 | transcribe | 9, 8, 7, 6, 5। / 4, 3, 2, 1, 0। | 9876543210 | yes | 0.427 |
| 300 | verbatim | नौ आठ सात छह पाँच। / चार तीन दो एक शून्य। | 9876543210 | yes | 0.488 |
| 300 | codemix | नौ, आठ, सात, छः, पाँच। / चार तीन दो एक शून्य। | 9876543210 | yes | 0.817 |
| 300 | transcribe | 9, 8, 7, 6, 5। / 43210 | 9876543210 | yes | 0.545 |
| 500 | verbatim | नौ आठ सात छह पाँच। / चार तीन दो एक शून्य। | 9876543210 | yes | 0.738 |
| 500 | codemix | नौ, आठ, सात, छः, पाँच। / चार तीन दो एक शून्य। | 9876543210 | yes | 1.097 |
| 500 | transcribe | 9, 8, 7, 6, 5। / 43210 | 9876543210 | yes | 0.738 |

## Realtime repeat: 10 different numbers at the best setting (200 ms, verbatim)

| Number | Pause s | Segments | Digits heard | Correct | Text after pause (s) |
|---|---|---|---|---|---|
| 9876543210 | 0.6 | नौ आठ सात छह पाँच। / चार तीन दो एक शून्य। | 9876543210 | yes | 0.39 |
| 8260181590 | 0.8 | आठ दो छः शून्य एक। / आठ एक पाँच नौ शून्य। | 8260181590 | yes | 0.362 |
| 7016613186 | 1.0 | सात शून्य एक छः छः। / एक तीन एक आठ छः। | 7016613186 | yes | 0.387 |
| 6913909960 | 0.6 | छः नौ एक तीन नौ। / शून्य नौ नौ छह शून्य। | 6913909960 | yes | 0.401 |
| 7082462819 | 0.8 | सात शून्य आठ दो चार। / छः दो आठ एक नौ। | 7082462819 | yes | 0.361 |
| 8821993518 | 1.0 | आठ आठ दो एक नौ। / नौ तीन पाँच एक आठ। | 8821993518 | yes | 0.368 |
| 6909378657 | 0.6 | छः नौ शून्य नौ तीन। / सात, आठ, छः, पाँच, सात। | 6909378657 | yes | 0.405 |
| 9543231948 | 0.8 | नौ, पाँच, चार, तीन, दो। / तीन एक नौ चार आठ। | 9543231948 | yes | 0.416 |
| 9574911862 | 1.0 | नौ पाँच सात चार नौ। / एक एक आठ छह दो। | 9574911862 | yes | 0.529 |
| 8276018955 | 0.6 | आठ दो सात छः शून्य। / एक आठ नौ पाँच पाँच। | 8276018955 | yes | 0.393 |

## Commit frame

Server window 2000 ms, commit sent 0.25 s into a 1.0 s pause. First text arrived 0.449 s after the pause began. Segments: नौ आठ सात छह पाँच। / चार तीन दो एक शून्य।.

## Two streams at once

- Stream 1: ok, 2 transcripts, 0 error events
- Stream 2: ok, 2 transcripts, 0 error events

## Re-listen: REST transcription of the audio so far, sent at the pause

- First group correct: 10 of 10
- Round trip: median 0.75 s, slowest 1.51 s

| Number | Transcript | Digits heard | Correct | Round trip s |
|---|---|---|---|---|
| 9876543210 | 9, 8, 7, 6, 5। | 98765 | yes | 0.767 |
| 8260181590 | 82601 | 82601 | yes | 0.726 |
| 7016613186 | 70166 | 70166 | yes | 0.863 |
| 6913909960 | 69139 | 69139 | yes | 0.685 |
| 7082462819 | 70824 | 70824 | yes | 0.72 |
| 8821993518 | 88219 | 88219 | yes | 0.824 |
| 6909378657 | 69093 | 69093 | yes | 1.361 |
| 9543231948 | 9, 5, 4, 3, 2। | 95432 | yes | 0.689 |
| 9574911862 | 95749 | 95749 | yes | 0.608 |
| 8276018955 | 82760 | 82760 | yes | 1.512 |

## Partial results (undocumented `x-partials` header), 1500 ms window

The docs say the stream sends finished segments only. With the header `x-partials: true` it also sends `partial_transcript` events with running text.

| Number | First group shown after pause began (s) | Full number shown after speech ended (s) | Final after speech ended (s) | Final correct | Any wrong partial |
|---|---|---|---|---|---|
| 9876543210 | 0.944 | 0.641 | 1.801 | yes | no |
| 8260181590 | 1.04 | 1.206 | 1.742 | yes | no |
| 7016613186 | None | None | 1.977 | yes | yes |
| 6913909960 | 0.771 | None | 2.355 | yes | no |
| 7082462819 | 1.071 | 1.118 | 1.752 | yes | no |

## Calls made

- REST transcriptions: 13
- Realtime sessions: 27
- Speech syntheses: see `data/cache/tts/` (one file per distinct clip)

Credit cost is not returned by the API. Compare the dashboard balance before and after this run.

Raw events for every run are in `results/probe_raw.json`.
