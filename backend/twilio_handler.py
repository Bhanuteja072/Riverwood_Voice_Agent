from twilio.twiml.voice_response import Gather, VoiceResponse

# Twilio voice for fallback if not using ElevenLabs
TWILIO_VOICE = "Polly.Aditi"  # Indian English AWS Polly voice via Twilio


def make_gather_response(
    speech_text: str,
    action_url: str,
    voice_url: str | None = None,
    reprompt_url: str | None = None   # ← new
) -> str:
    """
    Build TwiML that:
    1. Plays the agent's audio (or speaks text)
    2. Listens for customer response
    3. If no speech detected, re-prompts once and listens again (same action_url
       so conversation history continues normally)
    4. If still no speech, says goodbye and hangs up
    Returns TwiML XML string.
    """
    response = VoiceResponse()

    gather = Gather(
        input="speech",           # listen for speech
        action=action_url,        # where to send customer's speech
        method="POST",
        speech_timeout="2",       # wait 1 second after customer stops speaking
        language="en-IN"          # Indian English only
    )

    if voice_url:
        # Play pre-generated ElevenLabs audio
        print("[TTS] Using ElevenLabs voice for this call.")
        gather.play(voice_url)
    else:
        # Fallback: Twilio reads the text directly
        print("[TTS] Using Twilio Polly.Aditi voice for this call.")
        gather.say(speech_text, voice=TWILIO_VOICE, language="en-IN")

    response.append(gather)



    # ── Fallback Gather: fires only if primary Gather got no speech ───────
    # Re-prompts the user and sends their response to the same action_url
    # so conversation history continues normally.
    reprompt_gather = Gather(
        input="speech",
        action=action_url,
        method="POST",
        speech_timeout="4",
        language="en-IN"
    )
    if reprompt_url:
        print("[TTS] Using ElevenLabs voice for re-prompt.")
        reprompt_gather.play(reprompt_url)   # ← ElevenLabs audio
    else:
        reprompt_gather.say(
            "Could you please speak a little louder and try again?",
            voice=TWILIO_VOICE,
            language="en-IN"
        )
    response.append(reprompt_gather)

    # If customer doesn't speak, re-prompt once
    response.say(
        "I'm sorry, I couldn't hear you. Please call us back at your convenience. Goodbye!",
        voice=TWILIO_VOICE,
        language="en-IN"
    )
    response.hangup()

    return str(response)


def make_voicemail_response(customer_name: str) -> str:
    """TwiML for when call goes to voicemail."""
    response = VoiceResponse()
    response.say(
        f"Hello, {customer_name}. This is Riya from Riverwood Projects LLP. "
        "I have an important update for you. "
        "Please call us back at 8572070707. "
        "Thank you.",
        voice=TWILIO_VOICE,
        language="en-IN"
    )
    response.hangup()
    return str(response)


def make_end_call_response(audio_url: str | None = None, ai_text: str = "") -> str:
    """TwiML to gracefully end the call. Plays ElevenLabs audio if available."""
    response = VoiceResponse()
    if audio_url:
        response.play(audio_url)
    else:
        farewell = ai_text or "Thank you very much. Have a wonderful day!"
        response.say(farewell, voice=TWILIO_VOICE, language="en-IN")
    response.hangup()
    return str(response)