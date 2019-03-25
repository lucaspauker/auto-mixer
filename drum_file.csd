<CsoundSynthesizer>
<CsOptions>
-o {output_file} -W
</CsOptions>
<CsInstruments>
sr = 44100
nchnls = 2

instr 1; hihat closed
  aamp      expon     1000,  0.1,   p4
  arand     rand      aamp
  outs arand, arand
endin

instr 2; kick
  k1  expon    p4, .2, 50
  aenv expon 1, p3, 0.01
  a1  poscil    10000, k1, 1
  outs a1*aenv, a1*aenv
endin
</CsInstruments>

<CsScore>
f1 0 1024 10 1

r {number_of_beats}
t0 {bpm}
i1 0      0.50 10
i1 0.5    0.50 10

i2 0      0.50  100
s
</CsScore>
</CsoundSynthesizer>
