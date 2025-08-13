#!/usr/bin/env python3
"""
Drop-in integration for Claude CLI with whisper voice recording.

Add this to your Claude CLI to enable /voice shortcuts:

    # In your Claude CLI main loop, before processing commands:
    if user_input == '/voice':
        from claude_integration import handle_voice_command
        voice_text = handle_voice_command()
        if voice_text:
            # Process voice_text as if the user typed it
            user_input = voice_text

Or use as a standalone proxy:
    python claude_integration.py
"""

import sys
import os
import subprocess
import whisper_recorder

class ClaudeVoiceProxy:
    """Proxy that adds voice recording to Claude CLI"""
    
    def __init__(self):
        self.recorder = whisper_recorder.get_recorder()
        self.claude_process = None
    
    def start_claude(self):
        """Start Claude CLI as subprocess"""
        try:
            # Try to start claude cli - adjust command as needed
            self.claude_process = subprocess.Popen(
                ['claude'],  # Adjust this to your Claude CLI command
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1
            )
            return True
        except FileNotFoundError:
            print("❌ Claude CLI not found. Make sure 'claude' is in your PATH")
            return False
    
    def handle_voice_command(self):
        """Handle /voice shortcut - returns transcribed text or None"""
        if self.recorder.is_recording():
            print("⏹️  Stopping recording...")
            text = self.recorder.stop_recording_and_transcribe()
            if text:
                print(f"📝 Transcribed: {text}")
                return text
            else:
                print("❌ No speech detected")
                return None
        else:
            print("🎤 Starting recording... (type /voice again to stop)")
            success = self.recorder.start_recording()
            if not success:
                print("❌ Failed to start recording")
            return None
    
    def run_proxy(self):
        """Run as proxy between user and Claude CLI"""
        print("🎤 Claude CLI with Voice Recording")
        print("Commands:")
        print("  /voice  - Start/stop voice recording")
        print("  /mic    - Select microphone")
        print("  /help   - Show this help")
        print("  All other commands are passed to Claude CLI")
        print("=" * 50)
        
        if not self.start_claude():
            return
        
        try:
            while True:
                user_input = input("claude> ").strip()
                
                if user_input == '/voice':
                    voice_text = self.handle_voice_command()
                    if voice_text:
                        # Send transcribed text to Claude
                        print(f"➤ Sending to Claude: {voice_text}")
                        user_input = voice_text
                    else:
                        continue  # Don't send anything to Claude
                
                elif user_input == '/mic':
                    self.recorder.select_microphone()
                    continue
                
                elif user_input == '/help':
                    print("\n📖 Voice Recording Commands:")
                    print("  /voice  - Start/stop voice recording")
                    print("  /mic    - Select microphone")
                    print("  /help   - Show this help")
                    print("\n💡 All other commands are sent to Claude CLI")
                    continue
                
                elif user_input in ['/quit', '/exit']:
                    break
                
                # Send command to Claude CLI
                if user_input and self.claude_process:
                    self.claude_process.stdin.write(user_input + '\n')
                    self.claude_process.stdin.flush()
                    
                    # Read and display Claude's response
                    # Note: This is simplified - real implementation would need
                    # more sophisticated handling of Claude's output
                    
        except KeyboardInterrupt:
            print("\n")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources"""
        if self.claude_process:
            self.claude_process.terminate()
        self.recorder.cleanup()


# Standalone functions for direct integration
def handle_voice_command():
    """
    Standalone function for integrating into existing Claude CLI.
    
    Usage in your Claude CLI:
        if user_input == '/voice':
            from claude_integration import handle_voice_command
            voice_text = handle_voice_command()
            if voice_text:
                # Process voice_text as normal input
                process_user_input(voice_text)
    """
    recorder = whisper_recorder.get_recorder()
    
    if recorder.is_recording():
        print("⏹️  Stopping recording...")
        text = recorder.stop_recording_and_transcribe()
        if text:
            print(f"📝 Transcribed: {text}")
            return text
        else:
            print("❌ No speech detected")
            return None
    else:
        print("🎤 Starting recording... (type /voice again to stop)")
        success = recorder.start_recording()
        if not success:
            print("❌ Failed to start recording")
        return None


def setup_microphone():
    """Setup function to select microphone"""
    recorder = whisper_recorder.get_recorder()
    recorder.select_microphone()


if __name__ == "__main__":
    # Run as standalone proxy
    proxy = ClaudeVoiceProxy()
    proxy.run_proxy()