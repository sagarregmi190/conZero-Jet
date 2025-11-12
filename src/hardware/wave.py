import tkinter as tk
import math
import random

class WaveAnimation:
    def __init__(self, parent_frame):
        self.parent = parent_frame
        self.system_power = False
        self.system_paused = False
        self.system_fault = False
        
        # Create canvas with higher resolution for smoother rendering
        self.canvas = tk.Canvas(parent_frame, bg="#071226", highlightthickness=0,
                               width=480, height=150)
        self.canvas.grid(row=5, column=0, columnspan=3, pady=(10, 0), sticky="s")
        
        # Animation variables
        self.phase = 0
        self.animation_id = None
        self.animation_running = False
        
        # Wave colors - pure blue tones
        self.wave_colors = {
            'primary': '#4FC3F7',
            'secondary': '#29B6F6',
            'tertiary': '#03A9F4'
        }
        
        # Particle system
        self.particles = []
        self.max_particles = 12
        self.init_particles()

    def init_particles(self):
        """Initialize floating particles"""
        for i in range(self.max_particles):
            self.particles.append({
                'x': random.uniform(0, 480),
                'offset': random.uniform(0, 2 * math.pi),
                'speed': random.uniform(0.8, 1.5),
                'amplitude': random.uniform(3, 8),
                'size': random.uniform(1.5, 3),
                'opacity': random.uniform(0.3, 0.8)
            })

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
        """Main animation loop with smooth 60fps"""
        if not self.animation_running:
            return
            
        self.draw_waves()
        self.phase += 0.05  # Smoother, more fluid motion
        self.animation_id = self.parent.after(16, self.animate)  # ~60fps

    def draw_waves(self):
        """Draw only blue waves with smooth gradients"""
        self.canvas.delete("all")
        
        # Draw floating waves with enhanced visuals
        self.draw_enhanced_waves()
        
        # Draw animated particles
        self.draw_enhanced_particles()

    def draw_enhanced_waves(self):
        """Draw multiple wave layers with smooth gradients and fills"""
        wave_base = 75
        
        # Wave configurations for layered effect - just blue waves
        wave_configs = [
            {
                'offset': 0,
                'color': self.wave_colors['tertiary'],
                'width': 1.5,
                'amplitude': [5, 2, 2],
                'frequency': [0.025, 0.035, 0.015],
                'phase_mult': [0.8, 1.1, 0.6],
                'alpha': 0.4
            },
            {
                'offset': -8,
                'color': self.wave_colors['secondary'],
                'width': 2,
                'amplitude': [6, 3, 2],
                'frequency': [0.04, 0.06, 0.02],
                'phase_mult': [1.2, 0.9, 0.7],
                'alpha': 0.5
            },
            {
                'offset': -16,
                'color': self.wave_colors['primary'],
                'width': 2.5,
                'amplitude': [8, 4, 3],
                'frequency': [0.03, 0.05, 0.02],
                'phase_mult': [1.0, 1.3, 0.7],
                'alpha': 0.6
            }
        ]
        
        # Draw waves from back to front
        for config in wave_configs:
            self.draw_wave_layer(wave_base, config)

    def draw_wave_layer(self, base_height, config):
        """Draw a single wave layer with fill"""
        points = []
        detail = 4  # Higher detail for smoother curves
        
        for x in range(-50, 530, detail):
            y = base_height + config['offset']
            
            # Combine multiple sine waves for organic motion
            for i, (amp, freq, phase_m) in enumerate(zip(
                config['amplitude'],
                config['frequency'],
                config['phase_mult']
            )):
                y += math.sin(x * freq + self.phase * phase_m) * amp
            
            points.extend([x, y])
        
        # Create filled area
        fill_points = points.copy()
        fill_points.extend([530, 150, -50, 150, -50, points[1]])
        
        # Draw filled polygon with semi-transparency effect
        self.canvas.create_polygon(
            fill_points,
            fill=config['color'],
            outline="",
            stipple='gray50' if config['alpha'] < 0.5 else '',
            tags="wave_fill"
        )
        
        # Draw smooth wave line
        self.canvas.create_line(
            points,
            fill=config['color'],
            width=config['width'],
            smooth=True,
            splinesteps=36,  # Smoother curves
            tags="wave_line"
        )

    def draw_enhanced_particles(self):
        """Draw floating particles with smooth motion"""
        for particle in self.particles:
            # Update particle position
            particle['x'] = (particle['x'] + particle['speed'] * 0.5) % 480
            
            # Calculate Y position based on wave motion
            base_y = 75 + (
                math.sin(particle['x'] * 0.03 + self.phase * particle['speed']) * 
                particle['amplitude']
            )
            
            # Add vertical floating motion
            float_offset = math.sin(
                self.phase * particle['speed'] + particle['offset']
            ) * 5
            
            y = base_y + float_offset - 20
            
            # Draw particle - pure blue
            size = particle['size']
            
            # Bright blue particle
            brightness = int((0.5 + math.sin(self.phase * 2 + particle['offset']) * 0.5) * 200) + 55
            particle_color = f'#{brightness//2:02x}{brightness//2 + 50:02x}{255:02x}'
            
            self.canvas.create_oval(
                particle['x'] - size, y - size,
                particle['x'] + size, y + size,
                fill=particle_color,
                outline="",
                tags="particle"
            )

    def cleanup(self):
        """Clean up animation"""
        self.stop_animation()

# Test the animation
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Pure Blue Waves")
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
                         bg="#1a2a3a", fg="#4FC3F7", font=("Rajdhani", 8, "bold"),
                         relief=tk.FLAT, padx=10, pady=5)
    power_btn.place(x=50, y=160)
    
    pause_btn = tk.Button(frame, text="PAUSE", command=toggle_pause,
                         bg="#1a2a3a", fg="#4FC3F7", font=("Rajdhani", 8, "bold"),
                         relief=tk.FLAT, padx=10, pady=5)
    pause_btn.place(x=150, y=160)
    
    # Status label
    status_label = tk.Label(frame, text="🌊 Pure Blue Waves Only", 
                           bg="#071226", fg="#81D4FA", font=("Rajdhani", 10, "bold"))
    status_label.place(x=240, y=160, anchor="center")
    
    root.mainloop()