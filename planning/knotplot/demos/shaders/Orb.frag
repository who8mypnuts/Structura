varying vec3 normal, lightDir;
uniform vec3  OrbColour;

void main() {
  float intensity;
  vec3 n;

  n = normalize(normal);
  intensity = max (dot (lightDir, n), 0.0); 
		
  gl_FragColor = vec4 (OrbColour * intensity, 1.0);
}
