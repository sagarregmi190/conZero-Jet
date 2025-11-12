import tkinter as tk
import math
import random

class WaveAnimation:
    def __init__(self, parent_frame):
        self.parent = parent_frame
        self.system_power = False
        self.system_paused = False
        self.system_fault = False
        
        # Create canvas
        self.canvas = tk.Canvas(parent_frame, bg="#071226", highlightthickness=0,
                               width=480, height=150)
        self.canvas.grid(row=5, column=0, columnspan=3, pady=(10, 0), sticky="s")
        
        # Animation variables
        self.phase = 0
        self.animation_id = None
        self.animation_running = False
        
        # Wave style matching the reference image
        self.wave_colors = ["#4FC3F7", "#4FC3F7", "#4FC3F7"]  # Deep blue tones

    def set_system_state(self, power_on=False, paused=False, fault=False, speed=0):
        """Control animation based on system state"""
        self.system_power = power_on
        self.system_paused = paused
        self.system_fault = fault
        
        if power_on and not paused and not fault:
            if not self.animation_running:
                self.start_animation()
        else:
            self.stop_animation()

    def start_animation(self):
        """Start animation loop"""
        if not self.animation_running:
            self.animation_running = True
            self.phase = 0
            self.animate()

    def stop_animation(self):
        """Stop animation loop"""
        self.animation_running = False
        if self.animation_id:
            self.parent.after_cancel(self.animation_id)
            self.animation_id = None
        self.canvas.delete("all")

    def animate(self):
        """Main animation loop"""
        if not self.animation_running:
            return
            
        self.draw_waves()
        self.phase += 0.08  # Smooth floating motion
        self.animation_id = self.parent.after(40, self.animate)

    def draw_waves(self):
        """Draw only waves - no text"""
        self.canvas.delete("all")
        
        # Draw floating waves in the background
        self.draw_floating_waves()

    def draw_floating_waves(self):
        """Draw continuous floating waves in background with filled area"""
        wave_height = 75  # Perfect position as requested
        
        # Main wave layer - continuous floating motion
        points = []
        for x in range(-50, 530, 8):  # Extended beyond canvas for seamless flow
            # Multiple frequencies for organic floating
            y = (wave_height + 
                 math.sin(x * 0.03 + self.phase) * 8 +
                 math.sin(x * 0.05 + self.phase * 1.3) * 4 +
                 math.sin(x * 0.02 + self.phase * 0.7) * 3)
            points.extend([x, y])
        
        # Create filled wave area
        fill_points = points.copy()
        # Close the polygon by adding bottom corners
        fill_points.extend([530, 150])  # Bottom right
        fill_points.extend([-50, 150])  # Bottom left
        fill_points.extend([-50, points[1]])  # Back to start
        
        # Draw filled wave area with semi-transparent color
        self.canvas.create_polygon(
            fill_points,
            fill="#4FC3F7",
            outline="",
            tags="wave_fill"
        )
        
        # Draw main wave outline on top
        self.canvas.create_line(
            points,
            fill="#4FC3F7",
            width=2.5,
            smooth=True,
            tags="wave_main"
        )
        
        # Secondary wave layer
        points2 = []
        for x in range(-50, 530, 8):
            y = (wave_height + 12 +
                 math.sin(x * 0.04 + self.phase * 1.2) * 6 +
                 math.sin(x * 0.06 + self.phase * 0.9) * 3)
            points2.extend([x, y])
        
        # Create filled area for secondary wave
        fill_points2 = points2.copy()
        fill_points2.extend([530, 150])
        fill_points2.extend([-50, 150])
        fill_points2.extend([-50, points2[1]])
        
        self.canvas.create_polygon(
            fill_points2,
            fill="#4FC3F7",
            outline="",
            tags="wave_fill_secondary"
        )
        
        self.canvas.create_line(
            points2,
            fill="#4FC3F7",
            width=2,
            smooth=True,
            tags="wave_secondary"
        )
        
        # Third wave layer
        points3 = []
        for x in range(-50, 530, 8):
            y = (wave_height + 20 +
                 math.sin(x * 0.025 + self.phase * 0.8) * 5 +
                 math.sin(x * 0.035 + self.phase * 1.1) * 2)
            points3.extend([x, y])
        
        # Create filled area for third wave
        fill_points3 = points3.copy()
        fill_points3.extend([530, 150])
        fill_points3.extend([-50, 150])
        fill_points3.extend([-50, points3[1]])
        
        self.canvas.create_polygon(
            fill_points3,
            fill="#4FC3F7",
            outline="",
            tags="wave_fill_tertiary"
        )
        
        self.canvas.create_line(
            points3,
            fill="#4FC3F7",
            width=1.5,
            smooth=True,
            tags="wave_tertiary"
        )
        
        # Add subtle particles/dots floating with waves
        self.draw_floating_particles(wave_height)

    def draw_floating_particles(self, base_height):
        """Add floating particles that move with the waves"""
        for i in range(8):
            x = (self.phase * 20 + i * 60) % 520
            wave_y = (base_height + 
                     math.sin(x * 0.03 + self.phase) * 8 +
                     math.sin(x * 0.05 + self.phase * 1.3) * 4)
            
            # Random particle appearance
            if random.random() < 0.6:
                size = random.uniform(1, 2.5)
                self.canvas.create_oval(
                    x - size, wave_y - size,
                    x + size, wave_y + size,
                    fill="#FFFFFF",
                    outline="",
                    tags="particle"
                )

    def cleanup(self):
        """Clean up animation"""
        self.stop_animation()

# Test the animation
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Pure Wave Animation")
    root.geometry("480x200")
    root.configure(bg="#071226")
    
    frame = tk.Frame(root, bg="#071226")
    frame.pack(fill=tk.BOTH, expand=True)
    
    wave_anim = WaveAnimation(frame)
    
    # Start animation immediately
    wave_anim.set_system_state(power_on=True, paused=False, fault=False, speed=50)
    
    # Test controls
    def toggle_power():
        current = wave_anim.system_power
        wave_anim.set_system_state(power_on=not current, paused=False, fault=False, speed=50)
        power_btn.config(text="POWER OFF" if not current else "POWER ON")
    
    def toggle_pause():
        if wave_anim.system_power:
            current = wave_anim.system_paused
            wave_anim.set_system_state(power_on=True, paused=not current, fault=False, speed=50)
            pause_btn.config(text="RESUME" if not current else "PAUSE")
    
    power_btn = tk.Button(frame, text="POWER OFF", command=toggle_power, 
                         bg="#1a2a3a", fg="#4FC3F7", font=("Rajdhani", 8))
    power_btn.place(x=50, y=160)
    
    pause_btn = tk.Button(frame, text="PAUSE", command=toggle_pause,
                         bg="#1a2a3a", fg="#4FC3F7", font=("Rajdhani", 8))
    pause_btn.place(x=150, y=160)
    
    # Status label
    status_label = tk.Label(frame, text="Pure waves only - no text", 
                           bg="#071226", fg="#81D4FA", font=("Rajdhani", 9))
    status_label.place(x=240, y=160, anchor="center")
    
    root.mainloop()