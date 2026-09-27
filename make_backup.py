"""Render a silent, explicitly reconstructed backup of the observed rehearsal."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

root = Path(__file__).resolve().parent
font_path = Path('C:/Windows/Fonts/segoeui.ttf')
bold_path = Path('C:/Windows/Fonts/segoeuib.ttf')
font = lambda size, bold=False: ImageFont.truetype(str(bold_path if bold else font_path), size)
scenes = [
    ('01 / Find the gap', 'A critical step was missed.',
     ['Receipt evidence: diagnostic incorrect', 'Other diagnostic answers: correct', 'Course completion alone does not establish readiness.']),
    ('02 / Agent chooses', 'Coach the observed gap.',
     ['Live agent selected the approved receipt lesson.', 'Four eligible choices; receipt evidence was critical.', 'The saved decision identifies the source and prior evidence.']),
    ('03 / Prove understanding', 'Fresh cases establish readiness.',
     ['Reading alone did not award a pass.', 'Four objectives demonstrated through fresh cases.', 'Backend state: READY for the original procedure.']),
    ('04 / Procedure changes', 'Trainer reviews version two.',
     ['New rule: obtain a written Finance exception', 'when the supplier cannot replace a missing receipt.', 'Source, lessons, answer keys and mapping were reviewed.']),
    ('05 / Target the refresher', 'Three carried. One changed.',
     ['Three unchanged objective records carried forward.', 'Receipt evidence required an updated lesson and fresh case.', 'Earlier attempts remained in version history.']),
    ('06 / Close the loop', 'Ready for the updated procedure.',
     ['The learner correctly applied the Finance-exception rule.', 'Backend state: READY for version two.', 'Evidence of this workflow; no measured time-savings claim.']),
]
frames = []
for index, (label, title, lines) in enumerate(scenes):
    canvas = Image.new('RGB', (1280, 720), '#f5f7ee')
    draw = ImageDraw.Draw(canvas)
    draw.text((64, 42), 'AgentX Learn', font=font(32, True), fill='#254e40')
    draw.text((64, 108), 'OFFLINE REPLAY · RECONSTRUCTED FROM OBSERVED RESULTS', font=font(20, True), fill='#65745d')
    draw.rounded_rectangle((48, 167, 1232, 605), radius=24, fill='white')
    draw.text((80, 196), label, font=font(25, True), fill='#52734a')
    draw.text((80, 258), title, font=font(43, True), fill='#254e40')
    for row, line in enumerate(lines):
        draw.text((80, 357 + row*56), line, font=font(27), fill='#344b43')
    draw.text((64, 643), 'Fictional rehearsal · Not a screen recording · No live requests', font=font(21), fill='#65745d')
    for n in range(6):
        draw.rounded_rectangle((1020+n*29, 651, 1039+n*29, 660), radius=4, fill='#254e40' if n == index else '#d5decf')
    frames.append(canvas)
frames[0].save(root/'backup-demo.gif', save_all=True, append_images=frames[1:], duration=12000, loop=0)
frames[-1].save(root/'backup-demo-preview.png')
print('Created backup-demo.gif (72-second silent illustrated replay) and preview.')
