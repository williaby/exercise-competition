"""Rotating jokes for the leaderboard page.

A curated collection of brotherly roasts targeting Nick, the youngest Williams brother.
A random joke is selected on each page load.

Categories:
- PA vs MD (the credential gap)
- Endocrinology / metabolism irony
- Philosophy & History degrees
- Leaderboard / competition performance
- Family hierarchy & dynamics
- Bruce's age vs Nick's youth
- Kids roasting him
- Youngest child classics
- Golden retriever dad energy
- Boring, Oregon
- OHSU pipeline
- Philosophical references
- The Williams Family Medical Hierarchy
- Deep-cut clinical burns
- Existential & career trajectory burns
- Leaderboard-specific zingers
"""

from __future__ import annotations

import random

NICK_JOKES: list[str] = [
    # =====================================================================
    # PA vs MD — The Credential Gap (35%)
    # =====================================================================
    "Nick introduces himself as 'almost a doctor' and hopes nobody asks follow-up questions.",
    "Nick is a PA, which stands for 'Practically Actual... no wait, not quite.'",
    "Nick went to medical school adjacent. Like how a garage is house adjacent.",
    "Somewhere between a nurse and a doctor, there's Nick, filling out paperwork.",
    "Nick can prescribe medication but not respect. That requires an MD.",
    "Nick's dad is a doctor. His brother is a doctor. His wife is a doctor. Nick is a PA.",
    "Three Williams went to OHSU. Two came out as doctors. Nick came out as Nick.",
    "Nick's family tree has more MDs than a hospital directory. And then there's Nick.",
    "At Williams family dinners, Nick sits at the kids' table. Professionally speaking.",
    "Rachel has a DVM. Justin has an MD. Bruce has an MD. Byron has a CPA. Nick has excuses.",
    "Nick's wife literally outranks him in medicine. She's a veterinarian — an actual doctor.",
    "Rachel can perform surgery on a golden retriever. Nick can check your thyroid. Same energy.",
    "Nick tells people he's 'in medicine.' Technically, so is the receptionist.",
    "The Williams medical hierarchy: MD, MD, DVM, CPA, and then whatever Nick is.",
    "Nick is the only Williams who has to explain what his credential means at parties.",
    "Byron never claimed to be medical. That's a cleaner position than 'almost doctor.'",
    "Nick's PA badge is basically a participation trophy from OHSU.",
    "If the Williams family were a hospital, Nick would be middle management.",
    "Two MDs, a DVM, a CPA, and a PA walk into a bar. The PA picks up the tab because he has the most to prove.",
    "Nick didn't fail medical school. He just took the scenic route to a lesser destination.",
    "When Nick says 'trust me, I'm a doctor,' his own family starts laughing.",
    "The Williams family has an MD-to-PA conversion rate of 66%. Nick is the 34%.",
    "Nick went to the same school as his dad and brother. They got MDs. He got a consolidation prize.",
    "PA-C: the C stands for 'Close enough.'",
    "PA-C: Pretty Almost a Clinician.",
    "PA school is just medical school with a participation trophy at the end.",
    "Nick once said 'PAs practice medicine too.' And Applebee's practices cooking.",
    "Nick chose endocrinology because he wanted to be close to the word 'doctor' without actually being one.",
    "Nick spent 6 years studying History and Philosophy just to end up assisting someone who actually finished medical school.",
    "Nick literally studied the history of medicine and then decided to stop one degree short of practicing it.",
    "Nick's diploma from OHSU is the same size as Justin's. That's where the similarities end.",
    "Rachel went to vet school and became a doctor. Nick went to OHSU and became adjacent.",
    "At Thanksgiving, the MDs carve the turkey. Nick supervises.",
    # =====================================================================
    # Endocrinology / Metabolism Irony (15%)
    # =====================================================================
    "Nick chose endocrinology because he relates to hormones — always overreacting.",
    "Nick can regulate your thyroid but can't regulate his exercise schedule.",
    "Imagine spending a decade in medical training just to tell people their thyroid is slow. Nick relates.",
    "Nick treats hormone imbalances all day, then goes home and eats ice cream for dinner like a balanced adult.",
    "Nick knows everything about metabolism. Hasn't helped his leaderboard position one bit.",
    "Nick has a 'special interest in thyroid diseases.' His leaderboard ranking is the real disease.",
    "Nick manages metabolisms for a living and still can't manage to exercise consistently.",
    "Nick can explain basal metabolic rate to the molecular level. Can't convert that knowledge into points.",
    "Nick's patients trust him with their hormones. His brothers don't trust him with a two-day exercise streak.",
    "The man who treats metabolic disorders is losing a fitness competition. Let that sink in.",
    "Nick prescribes lifestyle changes to patients all day, then does the opposite at home.",
    "Imagine specializing in endocrinology — the study of hormones and metabolism — and losing a fitness competition to your father.",
    "Nick can explain the hypothalamic-pituitary-adrenal axis in clinical detail but can't explain why he's in last place.",
    "Nick treats thyroid disorders all day. Somewhere, his own thyroid is asking for a real doctor.",
    "Nick's endocrinology patients have better metabolic outcomes than he does.",
    "If Nick spent as much time exercising as he did explaining that PAs can do 'basically everything a doctor can,' he'd be in first place.",
    "Nick tells patients to exercise more and eat better for a living. This competition is his annual performance review.",
    "Nick's clinic bio says he makes 'an impact on patients' lives.' His impact on the leaderboard is less inspiring.",
    "Nick thoroughly enjoys being a collaborative part of his patients' health journey. His own health journey has detours.",
    "Salem Endocrinology's finest, ladies and gentlemen. Check the leaderboard for his fitness credentials.",
    "Nick can tell you exactly which hormones control weight gain. Still won't help him win.",
    "Somewhere in Salem, Nick is telling a patient to exercise more while actively losing this competition.",
    "Nick counsels patients on the dangers of a sedentary lifestyle, then sits down to check his leaderboard ranking.",
    "Nick's endocrinology training covered every gland in the human body. None of them are helping him win.",
    "Nick adjusts hormone levels for optimal health outcomes. His own optimal outcome is apparently fourth place.",
    "Nick can spot an underactive thyroid from across the room but can't spot two free days to exercise.",
    "Nick writes 'increase physical activity' on patient care plans with the confidence of a man not losing a fitness competition.",
    "Nick's patients come in with slow metabolisms. Nick comes in with slow leaderboard progress. It's a support group.",
    "Nick optimizes cortisol, insulin, and testosterone levels for patients. His own levels are optimized for disappointment.",
    "Nick spent years studying the endocrine system — the body's engine. His engine is in park.",
    # =====================================================================
    # Philosophy & History Degrees (15%)
    # =====================================================================
    "Nick and Justin both studied Philosophy in Oregon. One became an MD. One became a cautionary tale.",
    "Nick minored in Philosophy so he could rationalize his losses more eloquently.",
    "A History degree, a Philosophy minor, and a Human Physiology degree walk into a PA program.",
    "Nick studied History at U of O. Now he's making history as the worst-performing metabolism expert in a fitness competition.",
    "Nick's Philosophy minor taught him to ask 'What is the good life?' Apparently not one where you finish medical school.",
    "With a History degree, Nick is uniquely qualified to document his own competitive decline.",
    "Nick studied the great thinkers. None of them said 'stop at PA.'",
    "Justin's Philosophy degree led to an MD. Nick's Philosophy minor led to a participation award.",
    "Nick can explain Kant's categorical imperative. Kant's actual imperative: finish medical school.",
    "Descartes said 'I think, therefore I am.' Nick thinks, therefore he is... not a doctor.",
    "Socrates said the unexamined life isn't worth living. Nick's leaderboard position has been thoroughly examined.",
    "Nick studied Nietzsche: 'What doesn't kill you makes you stronger.' Medical school apparently almost killed him.",
    "Plato's Allegory of the Cave: prisoners mistake shadows for reality. Nick mistakes a PA for a doctor.",
    "Sartre said 'Hell is other people.' For Nick, hell is other people with MDs.",
    "The Myth of Sisyphus is about endlessly pushing a boulder uphill. Nick relates — he checks the leaderboard every week.",
    "Marcus Aurelius wrote about enduring hardship with dignity. Nick endures this leaderboard with... less dignity.",
    "Aristotle asked 'What is the ultimate good?' For Nick, apparently not an MD.",
    "Hippocrates said 'First, do no harm.' Nick said 'Second, do no medical school.'",
    "Epicurus said the good life requires simple pleasures. Like not having to explain your credential at family dinner.",
    "Nick has a History degree and a Philosophy minor. That's two ways to think deeply about why you're not a doctor.",
    "History degree, Philosophy minor, PA certificate. Nick collected credentials like Pokémon but stopped before the evolution.",
    "Nick studied Human Physiology at Oregon and still chose the career path with the fewest years of school. Coincidence?",
    "Somewhere, a high school guidance counselor is updating their 'what not to do' PowerPoint with Nick's transcript.",
    "Nick's Philosophy minor taught him to ask 'Why?' His career answers it: 'Because medical school was too hard.'",
    "Nick works in endocrinology, where he helps patients optimize their hormones. His own cortisol spikes every time someone calls Justin 'Doctor Williams.'",
    # =====================================================================
    # Leaderboard / Competition Performance (15%)
    # =====================================================================
    "Nick is the youngest competitor and has the fewest excuses. He's finding new ones anyway.",
    "If Nick can't beat a 70-year-old retired physician in a fitness competition, what was the point of Human Physiology?",
    "Nick is 39. He works in medicine. He exercises outdoors regularly. He should be dominating. He is not.",
    "The leaderboard doesn't care about your thyroid specialty, Nick.",
    "Nick's competition strategy is the same as his medical career: show up and hope nobody notices the gap.",
    "Every week Nick doesn't win is another week the family group chat stays undefeated.",
    "Nick hiking with his golden retrievers does not count as competition exercise. We checked.",
    "Nick's exercise routine: hike once, check leaderboard, contemplate philosophy, repeat.",
    "The competition is 20 weeks. Nick's excuses are on pace for 40.",
    "Two days a week, Nick. That's all we ask. Your patients would be disappointed.",
    "Nick snowshoes, backpacks, and hikes. But can he check a box on a website twice a week?",
    # =====================================================================
    # Family Hierarchy & Dynamics (10%)
    # =====================================================================
    "At Williams family gatherings, Nick's professional title gets an asterisk.",
    "Holiday seating chart: Doctor, Doctor, Doctor (of veterinary medicine), Accountant, Nick.",
    "The Williams family doesn't have a black sheep. They have a PA sheep.",
    "Byron built this entire app just to roast Nick. That's brotherhood.",
    "Byron controls the leaderboard, the jokes, and Nick's self-esteem. That's what big brothers are for.",
    "Nick grew up watching his dad be a real doctor for the whole town. Then chose the off-brand version.",
    "Three older brothers, and Nick still couldn't figure out that the path was: OHSU → MD, not OHSU → PA.",
    "The Williams family produces doctors the way Oregon produces rain. Nick is the drought.",
    "Nick was baptized in 1995. His competitive spirit was buried there too.",
    "Byron, Justin, Nick, and Bruce: a CPA, an OB/GYN, a PA, and a retired family doc walk into a fitness competition. The PA loses.",
    "Nick is the only Williams brother whose credential needs a hyphen and a footnote.",
    # =====================================================================
    # Bruce's Age vs Nick's Youth (5%)
    # =====================================================================
    "Bruce is in his 70s, retired, and still competing. Nick is 39 with a metabolism specialty. No pressure.",
    "If Bruce beats Nick in any given week, Nick should have to surrender his endocrinology certification.",
    "Bruce practiced medicine for 39 years. Nick has been alive for 39 years. Only one of those is impressive.",
    "Bruce is a retired MD who practiced for four decades. Nick works in Salem and loses fitness competitions.",
    "A man who retired from medicine is outworking the man who currently practices it. Classic Williams energy.",
    "Bruce doesn't need to check Nick's thyroid to know what's wrong. It's called not exercising.",
    # =====================================================================
    # Kids Roasting Nick (3%)
    # =====================================================================
    "Elanor is 8 and already knows a PA isn't a real doctor. Kids are perceptive.",
    "Brysen is 6 and calls his mom 'the real doctor in the family.' Rachel didn't correct him.",
    "Nick's kids ask him medical questions and then say 'we'll ask Mom to be sure.'",
    "Elanor told her class her mom is a doctor and her dad is 'like a helper doctor.'",
    "Nick's kids asked if he's a real doctor. Rachel said 'Even the dog has a better provider.'",
    "Nick's daughter Elanor will probably be a doctor someday. Then she can supervise him too.",
    "Even Nick's golden retrievers have more letters after their name. AKC > PA-C.",
    # =====================================================================
    # Youngest Child Classics
    # =====================================================================
    "Nick's baby photos are still in the 'Recent' folder.",
    "Nick didn't pick his own outfit until he was 27.",
    "Being the youngest means Nick's entire childhood was a hand-me-down experience.",
    "Nick still gets carded — not for alcohol, for the kids' menu.",
    "Nick's first word was 'me too' because that's all youngest kids ever say.",
    "Nick thinks 'hand-me-down' is a clothing brand.",
    "As the youngest, Nick's curfew was whenever his brothers got tired of babysitting.",
    "Nick's childhood nickname was 'Also Coming' as in 'we're bringing the boys — and Nick is also coming.'",
    "Nick learned to run fast. He had to — three older brothers, one bathroom.",
    "The youngest child doesn't have trust issues. They have 'my brothers told me the ice cream truck plays music when it's out of ice cream' issues.",
    "Nick's entire personality was formed by losing arguments to people who could bench press him.",
    "Being the youngest means your first bike was already on its fourth owner.",
    "Nick didn't get a new anything until he had his own paycheck.",
    "As the baby of the family, Nick's toughest workout is still trying to get a word in at dinner.",
    "Nick peaked at age 5 when he could still play the 'I'm telling Mom' card.",
    "The youngest child's superpower is weaponized tattling. Nick went pro.",
    "Nick's childhood was basically a spectator sport — watching his brothers do everything first.",
    "Nick still flinches when someone says 'stop copying me.'",
    "Three older brothers means Nick's pain tolerance is elite. His dignity, not so much.",
    "Nick's origin story is just his parents saying 'might as well try one more time.'",
    "Youngest child privilege is real — Nick got away with everything because his parents were too tired to care.",
    "Nick was raised by three brothers and it shows.",
    "The only thing Nick got first was the blame.",
    "Nick's favorite childhood game was 'Why are you hitting yourself?'",
    "Nick's childhood was 90% being told 'you're too young' and 10% being told 'you should know better by now.'",
    "Nick didn't learn to fight. He learned to run, hide, and negotiate — the three pillars of youngest child survival.",
    "Nick's first complete sentence was 'that's not fair' and he hasn't stopped saying it since.",
    "The youngest child never picks the movie, the restaurant, or the car seat. Nick's entire worldview was shaped by the middle seat of a minivan.",
    "Nick grew up thinking his name was 'And Nick' because every family introduction ended with it.",
    "As the youngest, Nick's opinion at family meetings had the same weight as the dog's.",
    "Nick's childhood coping mechanism was charm. It's the only reason he survived three older brothers.",
    "The youngest child is always the funniest in the family. It's a survival adaptation. Nick adapted.",
    "Nick didn't get to choose his own haircut until he left for college. Three brothers, zero democracy.",
    "Being the youngest means every family photo has Nick in whatever was left after his brothers picked their outfits.",
    "Nick's childhood bedroom was whatever room was left. His closet was whatever fit after hand-me-downs.",
    "The youngest child's love language is 'finally being included.' Nick is still waiting.",
    "Nick learned diplomacy early. When you're the smallest person in every argument, you negotiate or you lose.",
    "As the baby, Nick's role at family gatherings hasn't changed in 39 years: show up, get roasted, say nothing.",
    "Nick's entire childhood was a beta test. His brothers were the finished product.",
    # =====================================================================
    # Golden Retriever Dad Energy (1%)
    # =====================================================================
    "Nick's hobbies include hiking with golden retrievers and losing fitness competitions. Peak retriever dad energy.",
    "Nick has big golden retriever energy: loyal, enthusiastic, and no idea he's losing.",
    # =====================================================================
    # Boring, Oregon (1%)
    # =====================================================================
    "Nick got married in Boring, Oregon. The town named itself after his leaderboard performance.",
    "Nick and Rachel's wedding was in Boring, Oregon. The universe was trying to tell him something.",
    "Nick's wedding was in Boring, Oregon. The town was named after his pace on the leaderboard.",
    # =====================================================================
    # OHSU Pipeline
    # =====================================================================
    "OHSU accepted three Williams men. Two left as doctors. One left as Nick.",
    "The OHSU admissions office has seen the Williams family three times. Two out of three ain't bad.",
    "Bruce: OHSU → MD. Justin: OHSU → MD. Nick: OHSU → 'Well, he tried.'",
    "Bruce went to OHSU and became an MD. Justin went to OHSU and became an MD. Nick went to OHSU and became an assistant.",
    "Three Williams men walked into OHSU. Two walked out as doctors. One walked out as their helper.",
    "OHSU gave the Williams family two MDs and one PA. Even the admissions office has a sense of humor.",
    "Bruce got his MD in 1980. Justin got his MD in 2017. Nick got his participation certificate in between.",
    # =====================================================================
    # Clinic Bio Parody
    # =====================================================================
    "Nick's bio says he enjoys 'being a collaborative part of their health journey.' His brothers enjoy being a collaborative part of his public humiliation.",
    "Nick's clinic says 'outside of work you'll find him hiking with golden retrievers.' Inside of work you'll find him checking the leaderboard.",
    "'He thoroughly enjoys making an impact on patients' lives.' His impact on the scoreboard? Less thorough.",
    "Somewhere in Nick's office there's a motivational poster that says 'Believe in Yourself.' It was put up by his supervising physician.",
    # =====================================================================
    # The Williams Family Medical Hierarchy
    # =====================================================================
    "The Williams family medical hierarchy: MD, MD, DVM, CPA, PA. One of these is not like the others. One of these just didn't finish.",
    "Nick's wife fixes animals. Nick assists doctors. The family veterinarian outranks him.",
    "Rachel's patients can't talk and still respect her doctorate more than Nick's kids respect his PA.",
    "Rachel went to veterinary school — 4 years of doctorate-level education. Nick went to PA school — 2 years of 'close enough.'",
    "Rachel Rich became Rachel Williams and a DVM. Nick Williams stayed Nick Williams and a PA. She upgraded. He lateral-moved.",
    "PA school: 27 months. Medical school + residency: 7-8 years. The difference? People call you 'Doctor' at Thanksgiving.",
    "Nick's supervising physician has to co-sign his charts. Bruce and Justin just sign theirs.",
    "Nick's PA badge gets him into the hospital. Justin's MD badge gets him respect. There's a difference.",
    "Nick chose to work under a supervising physician. The rest of the family just calls that 'dinner with Dad.'",
    "Nick's wife outranks him medically. His brother outranks him medically. His dad outranks him medically. His kids outrank him in honesty.",
    # =====================================================================
    # Deep-Cut Clinical Burns
    # =====================================================================
    "Nick can diagnose a thyroid storm, an adrenal crisis, and a pheochromocytoma. He cannot diagnose why he's losing to retirees.",
    "Nick helps patients with Hashimoto's, Graves' disease, and adrenal insufficiency. His own diagnosis? Credential insufficiency.",
    "Nick prescribes levothyroxine all day. Someone should prescribe him some competitive drive.",
    "If Nick's leaderboard performance were a thyroid panel, his doctor would adjust the dosage immediately.",
    "If Nick's leaderboard rank were a lab result, it would be flagged with a red arrow pointing down.",
    "Nick's endocrinology patients get their TSH checked quarterly. Nick gets his ego checked every time he opens this leaderboard.",
    "Nick's endocrinology knowledge means he understands exactly which hormones are failing him in this competition. Clinically. In detail.",
    "Nick treats metabolic syndrome. Nick should maybe also screen himself.",
    "Nick treats endocrine disorders. The biggest hormonal imbalance in the family is Nick's testosterone-to-effort ratio in this competition.",
    "If effort were measured in thyroid hormone units, Nick would be profoundly hypothyroid right now.",
    "Nick's endocrine patients come to him with slow metabolisms. At least they have something in common.",
    "Nick helps patients whose bodies are working against them. He should feel right at home on this leaderboard.",
    "Nick treats people whose metabolisms don't work properly. This competition is peer review.",
    "Nick's endocrine patients trust him with their thyroid. His family won't trust him with the title 'Doctor.'",
    # =====================================================================
    # Existential & Career Trajectory Burns
    # =====================================================================
    "Nick's History degree: 4 years. Nick's Philosophy minor: additional coursework. Nick's PA program: 2 years. Nick's regret: lifelong.",
    "Nick was born 6 years after Byron, went to school for nearly as long, and emerged with roughly half the credential. Efficiency.",
    "Fun fact: Nick's PA-C and Byron's CPA have the same letters. Only one of them is honest about not being a doctor.",
    "Nick studied Human Physiology at UO, which means he understands in precise anatomical detail exactly how his body is failing him right now.",
    "Bruce hung up his stethoscope after 40 years of medicine. Nick hung up his chance at one after 2 years of PA school.",
    "Nick's History degree taught him about the fall of Rome. His leaderboard position is teaching him about the fall of Nick.",
    "Nick's UO transcript: History ✓ Philosophy ✓ Human Physiology ✓ Medical Degree ✗",
    "Fun fact: Nick's History degree makes him uniquely qualified to document the long and distinguished history of this leaderboard loss.",
    "The Williams boys all went to Oregon schools. Two of them finished. Byron never started. Nick... audited.",
    "If this competition measured 'years of education that didn't result in an MD,' Nick would be undefeated.",
    "Nick's Philosophy minor means he can construct an airtight logical argument for why PA is just as good as MD. No one in the family buys it.",
    "Nick studied Philosophy at Oregon. The only existential crisis bigger than his degree was choosing not to go to medical school.",
    "Nick's Philosophy minor covered ethics, logic, and metaphysics. None of those courses covered 'how to finish what you started.'",
    "Nick once contemplated Descartes' mind-body problem. Now he lives it — his mind says 'compete' and his body says 'nah.'",
    "Nick's History degree means he can tell you exactly when the PA profession was created: 1965. The MD? Ancient Greece. Choose your fighter.",
    "Nick studied the great philosophers. Kant said 'Act only according to that maxim whereby you can will that it should become a universal law.' Universal law: finish medical school.",
    # =====================================================================
    # Leaderboard-Specific Zingers
    # =====================================================================
    "Nick can order labs, interpret results, and develop treatment plans. He just can't order himself a first-place finish.",
    "Nick can prescribe medication in all 50 states. He just can't prescribe himself a win.",
    "Nick helps regulate other people's insulin sensitivity but can't regulate his own position on this leaderboard.",
    "Nick's bio mentions snowshoeing. Bold of a man losing a fitness competition to claim outdoor hobbies.",
    "Nick's clinic bio says he enjoys 'hiking, backpacking, and snowshoeing.' Strange that none of that cardio is showing up on this leaderboard.",
    "Nick works at Salem Endocrinology on Skyline Road. The only skyline he'll see in this competition is everyone else's back.",
    "Nick's supervising physician reviews his work. This leaderboard reviews his life choices.",
    "Nick's clinic says patients can 'Request an Appointment.' His family requests he request an MD program.",
    "Nick's clinic says he has 'a special interest in Thyroid diseases.' His family has a special interest in why he's not a doctor.",
    "Nick's clinic bio says he 'thoroughly enjoys making an impact on patients' lives.' His leaderboard position is making an impact on no one.",
    "Justin delivers babies. Bruce healed families for 40 years. Nick... assists.",
    "Bruce practiced family medicine for four decades. Nick practices family disappointment on a 20-week cycle.",
    "Nick's golden retrievers get more excited about a walk than Nick gets about this competition. And they'd probably finish faster.",
    "The Williams family holiday card: 'Season's Greetings from the Doctors Williams, and also Nick.'",
    "Justin teaches patients that education is the most important role of a physician. Nick's competition performance is educational for everyone.",
    "Nick married Rachel in Boring, OR. She became a DVM. He became a PA. Even the town knew the punchline before they did.",
    "Nick got married in Boring, Oregon, which is fitting because that's also how his competition results read.",
    "Nick treats patients with metabolic disorders 5 days a week, then comes home and gets outperformed by a man born during the Eisenhower administration.",
    "Bruce is in his 70s and still competing. Nick is 39 and already making excuses. The apple fell far from the tree and rolled downhill.",
    "Nick is the youngest, fittest Williams in this competition. When he loses, he doesn't even get an excuse.",
    "Nick's got a Philosophy minor and a History degree. That's a lot of thinking about the past for a guy with no future on this leaderboard.",
    "Nick's UO History degree focused on the past. His leaderboard position is focused on staying there.",
    "Brysen is 6 years old and already knows his mom is a real doctor and his dad is 'something else.' That kid is going places. Unlike Nick on this leaderboard.",
    "Nick's kids are 8 and 6. They already know the difference between MD and PA. Brutal honesty runs in the family.",
    "Nick's daughter Elanor is 8. At her current trajectory she'll have more education than Nick by age 26.",
    "PA-C stands for Physician Assistant - Certified. In the Williams family it stands for Pretty Adequate - Close enough.",
    "PA-C: two letters and a hyphen away from being taken seriously at family dinner.",
    "Nick is the only Williams brother whose credential needs a hyphen to seem longer.",
    "Nick works in endocrinology at Salem Endocrinology. His job title has more syllables than his credential.",
    "Nick's bio says he enjoys 'being a collaborative part of patients' health journey.' That's a long way of saying 'supervised.'",
    "The Williams Thanksgiving seating chart: Doctor, Doctor, Doctor of Veterinary Medicine, CPA, and Nick.",
    "Nick studied History at UO. The most relevant period? The part where physicians' assistants didn't exist yet.",
    "Nick's golden retrievers are the most loyal beings in his life. They don't care that he's not a real doctor.",
]


def get_random_joke() -> str:
    """Return a random joke from the collection."""
    return random.choice(NICK_JOKES)  # noqa: S311
