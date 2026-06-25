"""Fine-tune gpt-4o-mini on Kruthik's LinkedIn voice from voiceTest.md."""
import json
from pathlib import Path
from openai import OpenAI

CLIENT = OpenAI()
SYSTEM_PROMPT = Path("evolved_prompt.txt").read_text(encoding="utf-8").strip()

# 26 examples sourced directly from voiceTest.md short posts
TRAINING_PAIRS = [
    (
        "Write a LinkedIn post about content creation hooks and the value of nuanced thinking.",
        'Aren\'t you tired of creating and consuming content with "hooks"?\n\nWriting is a skill mainly used for communication and thought processing. Good communication includes nuance. Read from people who offer a nuanced perspective.',
    ),
    (
        "Write a LinkedIn post about the noise of the modern world and protecting your attention.",
        "The world is so noisy. Everyone is trying to grab your attention.\n\nIf you're reading this, go put your phone away and touch grass or just let yourself get bored.",
    ),
    (
        "Write a LinkedIn post about a community gathering focused on brain fitness and original thinking.",
        "A room full of people working together on their brain fitness. Their original creative ideas and thinking. This was Creative Brain lab.\n\nTogether we are fighting brain rot and challenging status quo.",
    ),
    (
        "Write a LinkedIn post about the lack of routine cognitive health screening in medicine.",
        "Your doctor doesn't test for your attention span or memory or cognition until it's too late.\n\nHow do you think you'd fare on it if they took a test today?",
    ),
    (
        "Write a LinkedIn post about the disappearance of boredom from modern life.",
        "What was the last time you were bored? Bored out of your mind?",
    ),
    (
        "Write a LinkedIn post about creativity requiring both divergent and convergent thinking.",
        "Creativity is the ability to generate novel ideas that are USEFUL.\n\nSo while we may think that creativity is mostly divergent thinking, convergence is needed for ideas to materialize. What do I mean?\n\nPracticing focus and exploration are both equally important to a healthy creative brain. They're the perfect couple.",
    ),
    (
        "Write a LinkedIn post about how the nervous system responds to non-physical threats like uncertainty and constant interruption.",
        "Your nervous system responds to more than obvious threats.\n\nUncertainty, unpredictability, and constant interruption can also keep the brain in a heightened state of vigilance.",
    ),
    (
        "Write a LinkedIn post about cognitive exhaustion that is not the same as physical tiredness.",
        "Some forms of exhaustion are less about physical energy and more about sustained cognitive demand.\n\nThe body may be still while the brain remains continuously engaged.",
    ),
    (
        "Write a LinkedIn post about the possibility of doctors testing attention span as a health metric in the future.",
        "It's possible that in 10 years your doctor will check your attention span and let you know that you need to work on it.\n\nBut for those who can't wait for another decade, tell me what frustrates you the most about your attention.",
    ),
    (
        "Write a LinkedIn post about how scrolling while exhausted is neurologically different from genuine rest.",
        "The brain does not treat all forms of rest equally.\n\nScrolling while exhausted is neurologically different from genuine cognitive recovery.",
    ),
    (
        "Write a LinkedIn post about how modern technology competes with the brain's attention filtering system.",
        "The brain is constantly filtering the world, deciding what deserves attention.\n\nModern technology competes aggressively for that filtering system.",
    ),
    (
        "Write a LinkedIn post comparing the brain's response to opening the fridge versus opening Instagram.",
        "You know the thing your brain does when you open the fridge and hope for something to magically appear?\n\nI think that's what happens when you open instagram - but this time you're rewarded. No actually, you're rewarded every single time.",
    ),
    (
        "Write a LinkedIn post about the growing value of sustained, single-topic attention in the age of constant interruption.",
        "The ability to stay with one thought for an extended period may become increasingly valuable in the age of constant interruption.",
    ),
    (
        "Write a LinkedIn post offering a simple brain rest exercise.",
        "Brain workout of the day: Set a timer for 90 seconds. Do absolutely nothing.",
    ),
    (
        "Write a LinkedIn post about attention as more than a productivity tool.",
        "Attention is not just a productivity tool.\n\nIt influences memory, emotional regulation, learning, and how deeply you experience your own life.",
    ),
    (
        "Write a LinkedIn post about how the environment affects attention recovery, and why the same problem feels easier after a walk.",
        "The brain appears to recover attention differently depending on the environment around you.\n\nThis may be why the same problem can feel impossible at your desk and clearer ten minutes into a walk.",
    ),
    (
        "Write a LinkedIn post about how a walk beneath trees helps untangle difficult thinking.",
        "There are days when your thoughts feel impossibly tangled.\n\nThen you take a walk beneath trees, look toward the horizon, and discover your mind has quietly begun solving things without you.",
    ),
    (
        "Write a LinkedIn post about the subtle, undramatic way cognitive fatigue shows up.",
        "Cognitive fatigue doesn't always feel dramatic.\n\nSometimes it feels like rereading the same sentence five times while your brain quietly asks for rest.",
    ),
    (
        "Write a LinkedIn post about the fundamental brain difference between consuming and creating content.",
        "Consuming and creating may both feel productive but they are fundamentally different for your brain.",
    ),
    (
        "Write a LinkedIn post questioning whether scrolling has become this generation's version of smoking.",
        "Is scrolling the smoking of our generation?\n\nDo you feel this?",
    ),
    (
        "Write a LinkedIn post about how the modern world trains reactive attention while neglecting depth and reflection.",
        "The modern world trains your attention toward constant reaction.\n\nVery little trains your brain to sustain depth, reflection, or uninterrupted thought.",
    ),
    (
        "Write a LinkedIn post about how the brain was not built for constant context switching.",
        'Your brain did not evolve to process hundreds of rapid context switches per day. What feels like "normal modern life" may actually be chronic attentional fragmentation.',
    ),
    (
        "Write a LinkedIn post about creating a pause between trigger and reaction as a form of brain training.",
        "All you need is a pause between your trigger and reaction. That little awareness of trigger creates space for you to train your brain.",
    ),
    (
        "Write a LinkedIn post about attention restoration theory and why best ideas don't arrive at a screen.",
        'Your best ideas rarely arrive while staring at the same screen for 8 hours.\n\nResearch suggests mentally demanding work fatigues "directed attention" I.e. the intense focus used for screens, emails, and problem solving.\n\nNatural environments appear to help the brain recover attention and think more flexibly.\n\nThis is part of the science of attention restoration.',
    ),
    (
        "Write a LinkedIn post about the trap of endlessly searching for quick fixes.",
        "You know in your heart that there are no quick fixes. And yet you look for them everywhere.",
    ),
    (
        "Write a LinkedIn post asking the community about undiagnosed ADHD, framed as personal research.",
        "Help me with this for personal research purposes.\n\nDo you think you have ADHD but haven't been formally diagnosed?",
    ),
]


def build_jsonl(output_path: str = "training_data.jsonl") -> str:
    lines = [
        json.dumps({
            "messages": [
                {"role": "system",    "content": SYSTEM_PROMPT},
                {"role": "user",      "content": user},
                {"role": "assistant", "content": assistant},
            ]
        })
        for user, assistant in TRAINING_PAIRS
    ]
    Path(output_path).write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {len(lines)} examples to {output_path}")
    return output_path


def upload_and_finetune(jsonl_path: str) -> str:
    print("Uploading training file...")
    with open(jsonl_path, "rb") as f:
        file_obj = CLIENT.files.create(file=f, purpose="fine-tune")
    print(f"File ID: {file_obj.id}")

    print("Starting fine-tune job on gpt-4o-mini-2024-07-18...")
    job = CLIENT.fine_tuning.jobs.create(
        training_file=file_obj.id,
        model="gpt-4o-mini-2024-07-18",
    )
    print(f"Job ID:  {job.id}")
    print(f"Status:  {job.status}")
    print()
    print("When status == 'succeeded', copy the fine_tuned_model string and")
    print("swap it into MODEL in app.py and generate_posts.py.")
    print(f"\nCheck status: python -c \"from openai import OpenAI; j=OpenAI().fine_tuning.jobs.retrieve('{job.id}'); print(j.status, j.fine_tuned_model)\"")
    return job.id


if __name__ == "__main__":
    jsonl = build_jsonl()
    upload_and_finetune(jsonl)
