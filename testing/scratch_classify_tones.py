import os
import json

def classify_dialogue(text):
    text_lower = text.lower()
    
    # Tone: soft_laugh
    # Keywords that suggest humor, irony, playfulness, lightheartedness, or odd/silly scenarios
    funny_keywords = [
        "funny", "silly", "ridiculous", "absurd", "ironic", "irony", "laugh", 
        "chuckle", "grin", "smile", "joke", "amusement", "weirdly", "bizarrely", 
        "odd", "strange", "weird", "mock", "mocking", "hilarious", "comic", "clown", 
        "sarcastic", "sarcasm", "playful", "giggle", "snicker", "jest", "curiously enough",
        "ironically", "foolish", "nonsense"
    ]
    
    # Tone: calm
    # Keywords that suggest quiet, darkness, reflection, nature, peace, sleeping, or transition
    calm_keywords = [
        "stillness", "quiet", "silent", "silence", "shadow", "night", "dark", 
        "peaceful", "peace", "forest", "rain", "mist", "cold", "calm", "breathe", 
        "slow", "resting", "sleeping", "sleep", "empty", "forgotten", "ancient", 
        "soft", "reflection", "dream", "breeze", "whisper", "somber", "gentle", 
        "slowly", "hushed", "dusk", "dawn", "twilight", "fade", "faded", "calmly",
        "softly", "peacefully", "lake", "moon", "star", "wind", "breathed", "rested"
    ]
    
    for kw in funny_keywords:
        if kw in text_lower:
            return "soft_laugh"
            
    for kw in calm_keywords:
        if kw in text_lower:
            return "calm"
            
    # Default/Mostly led tone is curious
    return "curious"

def main():
    manifest_path = "outputs/manifests/manifest.json"
    
    if not os.path.exists(manifest_path):
        print(f"Error: Manifest not found at {manifest_path}")
        return

    with open(manifest_path, "r") as f:
        data = json.load(f)

    beats = data.get("beats", [])
    
    print("=== Re-classifying Beat Tones dynamically based on dialogue context ===")
    
    counts = {"curious": 0, "calm": 0, "soft_laugh": 0}
    changes = []
    
    for beat in beats:
        if beat.get("type") == "narration" and beat.get("voice") and beat["voice"] != "none":
            dialogue = beat["dialogue"]
            old_tone = beat["voice"].get("tone")
            new_tone = classify_dialogue(dialogue)
            
            beat["voice"]["tone"] = new_tone
            counts[new_tone] += 1
            
            if old_tone != new_tone:
                changes.append(f"Beat {beat['id']}: Changed '{old_tone}' -> '{new_tone}' | Dialogue: '{dialogue[:70]}...'")
            else:
                # Keep track of assignments
                pass

    # Save the manifest
    with open(manifest_path, "w") as f:
        json.dump(data, f, indent=2)
        
    print(f"\nFinished updating manifest.json.")
    print(f"Total assignments - Curious: {counts['curious']}, Calm: {counts['calm']}, Soft Laugh: {counts['soft_laugh']}")
    print(f"Number of modified beat tones: {len(changes)}")
    
    if changes:
        print("\nDetail of updates:")
        for change in changes[:30]:
            print(f"  {change}")
        if len(changes) > 30:
            print(f"  ... and {len(changes) - 30} more changes.")

if __name__ == "__main__":
    main()
