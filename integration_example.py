#!/usr/bin/env python3
"""
Example integration of whisper_recorder into other CLIs like Codex or Claude.

This shows how to add voice recording shortcuts to existing REPL environments.
"""

import sys
import os

# Add current directory to path so we can import whisper_recorder
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import whisper_recorder

class ExampleREPL:
    """Example REPL showing how to integrate whisper recording"""
    
    def __init__(self):
        self.running = True
        self.recorder = whisper_recorder.get_recorder()
        
        # Set up shortcuts
        self.shortcuts = {
            '/voice': self._toggle_voice_recording,
            '/mic': self._select_microphone,
            '/help': self._show_help,
            '/quit': self._quit
        }
    
    def _toggle_voice_recording(self):
        """Toggle voice recording on/off"""
        if self.recorder.is_recording():
            print("⏹️  Stopping recording...")
            text = self.recorder.stop_recording_and_transcribe()
            if text:
                print(f"📝 Transcribed: {text}")
                # Here you would normally send this to your CLI's input handler
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
    
    def _select_microphone(self):
        """Select microphone"""
        self.recorder.select_microphone()
    
    def _show_help(self):
        """Show available shortcuts"""
        print("\n📖 Available shortcuts:")
        print("  /voice  - Start/stop voice recording")
        print("  /mic    - Select microphone")
        print("  /help   - Show this help")
        print("  /quit   - Exit")
        print("\n💡 Usage: Type /voice to start recording, speak, then type /voice again to transcribe")
    
    def _quit(self):
        """Quit the REPL"""
        self.running = False
        print("Goodbye!")
    
    def run(self):
        """Main REPL loop"""
        print("🤖 Example REPL with Whisper Integration")
        print("Type /help for available shortcuts")
        
        while self.running:
            try:
                user_input = input("\n> ").strip()
                
                # Check for shortcuts
                if user_input in self.shortcuts:
                    result = self.shortcuts[user_input]()
                    if result:  # If voice recording returned text
                        print(f"💬 You would send this to your CLI: '{result}'")
                        # In a real integration, you'd process this text as if the user typed it
                
                elif user_input.startswith('/'):
                    print(f"❓ Unknown shortcut: {user_input}")
                    print("Type /help for available shortcuts")
                
                else:
                    # Regular command processing
                    if user_input:
                        print(f"🔄 Processing command: {user_input}")
                        # Here you would process the regular command
                
            except KeyboardInterrupt:
                print("\n")
                self._quit()
            except EOFError:
                self._quit()
        
        # Cleanup
        self.recorder.cleanup()


# Integration functions for existing CLIs
def add_whisper_to_repl(repl_instance):
    """
    Helper function to add whisper functionality to an existing REPL.
    
    Usage:
        import whisper_recorder
        
        # In your REPL class __init__:
        self.recorder = whisper_recorder.get_recorder()
        
        # Add these methods to your REPL class:
        def handle_voice_shortcut(self):
            if self.recorder.is_recording():
                text = self.recorder.stop_recording_and_transcribe()
                if text:
                    # Process text as if user typed it
                    self.process_input(text)
            else:
                self.recorder.start_recording()
                print("🎤 Recording... (trigger shortcut again to stop)")
    """
    pass


# Simple functions for quick integration
def create_voice_shortcut_handler():
    """
    Returns a function that can be used as a shortcut handler in other CLIs.
    
    Usage in your CLI:
        from whisper_recorder import create_voice_shortcut_handler
        
        voice_handler = create_voice_shortcut_handler()
        
        # In your command handler:
        if command == '/voice':
            text = voice_handler()
            if text:
                self.process_input(text)
    """
    recorder = whisper_recorder.get_recorder()
    
    def voice_shortcut():
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
            print("🎤 Starting recording... (call again to stop)")
            recorder.start_recording()
            return None
    
    return voice_shortcut


if __name__ == "__main__":
    # Run the example REPL
    repl = ExampleREPL()
    repl.run()