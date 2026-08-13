import { Mesh, Program, Renderer, Triangle, Vec3 } from "ogl";
import { useEffect, useRef } from "react";
import "./Orb.css";

export type OrbMode = "idle" | "listening" | "speaking";

interface OrbProps {
  mode: OrbMode;
  audioLevel: number;
  hue?: number;
  hoverIntensity?: number;
  rotateOnHover?: boolean;
  forceHoverState?: boolean;
  backgroundColor?: string;
}

const vertexShader = /* glsl */ `
  precision highp float;
  attribute vec2 position;
  attribute vec2 uv;
  varying vec2 vUv;

  void main() {
    vUv = uv;
    gl_Position = vec4(position, 0.0, 1.0);
  }
`;

const fragmentShader = /* glsl */ `
  precision highp float;

  uniform float iTime;
  uniform vec3 iResolution;
  uniform float hue;
  uniform float hover;
  uniform float rot;
  uniform float hoverIntensity;
  uniform float speechActivity;
  uniform vec3 backgroundColor;
  varying vec2 vUv;

  vec3 rgb2yiq(vec3 color) {
    return vec3(
      dot(color, vec3(0.299, 0.587, 0.114)),
      dot(color, vec3(0.596, -0.274, -0.322)),
      dot(color, vec3(0.211, -0.523, 0.312))
    );
  }

  vec3 yiq2rgb(vec3 color) {
    return vec3(
      color.x + 0.956 * color.y + 0.621 * color.z,
      color.x - 0.272 * color.y - 0.647 * color.z,
      color.x - 1.106 * color.y + 1.703 * color.z
    );
  }

  vec3 adjustHue(vec3 color, float hueDegrees) {
    float angle = hueDegrees * 3.14159265 / 180.0;
    vec3 yiq = rgb2yiq(color);
    float cosine = cos(angle);
    float sine = sin(angle);
    yiq.yz = vec2(
      yiq.y * cosine - yiq.z * sine,
      yiq.y * sine + yiq.z * cosine
    );
    return yiq2rgb(yiq);
  }

  vec3 hash33(vec3 point) {
    point = fract(point * vec3(0.1031, 0.11369, 0.13787));
    point += dot(point, point.yxz + 19.19);
    return -1.0 + 2.0 * fract(vec3(
      point.x + point.y,
      point.x + point.z,
      point.y + point.z
    ) * point.zyx);
  }

  float noise3(vec3 point) {
    const float k1 = 0.333333333;
    const float k2 = 0.166666667;
    vec3 cell = floor(point + (point.x + point.y + point.z) * k1);
    vec3 d0 = point - (cell - (cell.x + cell.y + cell.z) * k2);
    vec3 edge = step(vec3(0.0), d0 - d0.yzx);
    vec3 i1 = edge * (1.0 - edge.zxy);
    vec3 i2 = 1.0 - edge.zxy * (1.0 - edge);
    vec3 d1 = d0 - (i1 - k2);
    vec3 d2 = d0 - (i2 - k1);
    vec3 d3 = d0 - 0.5;
    vec4 falloff = max(0.6 - vec4(
      dot(d0, d0),
      dot(d1, d1),
      dot(d2, d2),
      dot(d3, d3)
    ), 0.0);
    vec4 noise = falloff * falloff * falloff * falloff * vec4(
      dot(d0, hash33(cell)),
      dot(d1, hash33(cell + i1)),
      dot(d2, hash33(cell + i2)),
      dot(d3, hash33(cell + 1.0))
    );
    return dot(vec4(31.316), noise);
  }

  vec4 extractAlpha(vec3 color) {
    float alpha = max(max(color.r, color.g), color.b);
    return vec4(color / (alpha + 0.00001), alpha);
  }

  float lightLinear(float intensity, float attenuation, float distanceValue) {
    return intensity / (1.0 + distanceValue * attenuation);
  }

  float lightQuadratic(float intensity, float attenuation, float distanceValue) {
    return intensity / (1.0 + distanceValue * distanceValue * attenuation);
  }

  vec4 drawOrb(vec2 uv) {
    const float innerRadius = 0.6;
    const float noiseScale = 0.65;
    vec3 color1 = adjustHue(vec3(0.611765, 0.262745, 0.996078), hue);
    vec3 color2 = adjustHue(vec3(0.298039, 0.760784, 0.913725), hue);
    vec3 color3 = adjustHue(vec3(0.062745, 0.078431, 0.600000), hue);
    float angle = atan(uv.y, uv.x);
    float lengthValue = length(uv);
    float inverseLength = lengthValue > 0.0 ? 1.0 / lengthValue : 0.0;
    float backgroundLuminance = dot(backgroundColor, vec3(0.299, 0.587, 0.114));
    float n0 = noise3(vec3(uv * noiseScale, iTime * 0.5)) * 0.5 + 0.5;
    float radius = mix(mix(innerRadius, 1.0, 0.4), mix(innerRadius, 1.0, 0.6), n0);
    float edgeDistance = distance(uv, (radius * inverseLength) * uv);
    float rim = lightLinear(1.0, 10.0, edgeDistance);

    rim *= smoothstep(radius * 1.05, radius, lengthValue);
    float innerFade = smoothstep(radius * 0.8, radius * 0.95, lengthValue);
    rim *= mix(innerFade, 1.0, backgroundLuminance * 0.7);
    float colorBlend = cos(angle + iTime * 2.0) * 0.5 + 0.5;
    float lightAngle = iTime * -1.0;
    vec2 lightPosition = vec2(cos(lightAngle), sin(lightAngle)) * radius;
    float lightDistance = distance(uv, lightPosition);
    float movingLight = lightQuadratic(1.5, 5.0, lightDistance);
    movingLight *= lightLinear(1.0, 50.0, edgeDistance);
    float outerMask = smoothstep(1.0, mix(innerRadius, 1.0, n0 * 0.5), lengthValue);
    float innerMask = smoothstep(innerRadius, mix(innerRadius, 1.0, 0.5), lengthValue);
    vec3 colorBase = mix(color1, color2, colorBlend);
    float fadeAmount = mix(1.0, 0.1, backgroundLuminance);
    vec3 darkColor = mix(color3, colorBase, rim);
    darkColor = (darkColor + movingLight) * outerMask * innerMask;
    darkColor = clamp(darkColor, 0.0, 1.0);
    vec3 lightColor = (colorBase + movingLight) * mix(1.0, outerMask * innerMask, fadeAmount);
    lightColor = mix(backgroundColor, lightColor, rim);
    lightColor = clamp(lightColor, 0.0, 1.0);
    vec3 finalColor = mix(darkColor, lightColor, backgroundLuminance);

    return extractAlpha(finalColor);
  }

  void main() {
    vec2 center = iResolution.xy * 0.5;
    float size = min(iResolution.x, iResolution.y);
    vec2 uv = (vUv * iResolution.xy - center) / size * 2.0;
    float sine = sin(rot);
    float cosine = cos(rot);
    uv = vec2(cosine * uv.x - sine * uv.y, sine * uv.x + cosine * uv.y);
    float distortion = hover + speechActivity;
    uv.x += distortion * hoverIntensity * 0.1 * sin(uv.y * 10.0 + iTime);
    uv.y += distortion * hoverIntensity * 0.1 * sin(uv.x * 10.0 + iTime);
    vec4 color = drawOrb(uv);
    gl_FragColor = vec4(color.rgb * color.a, color.a);
  }
`;

export function Orb({
  mode,
  audioLevel,
  hue = 0,
  hoverIntensity = 2,
  rotateOnHover = true,
  forceHoverState = false,
  backgroundColor = "#000000",
}: OrbProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const modeRef = useRef(mode);
  const audioLevelRef = useRef(audioLevel);

  modeRef.current = mode;
  audioLevelRef.current = audioLevel;

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const renderer = new Renderer({ alpha: true, premultipliedAlpha: false });
    const gl = renderer.gl;
    const geometry = new Triangle(gl);
    const program = new Program(gl, {
      vertex: vertexShader,
      fragment: fragmentShader,
      transparent: true,
      uniforms: {
        iTime: { value: 0 },
        iResolution: { value: new Vec3() },
        hue: { value: hue },
        hover: { value: 0 },
        rot: { value: 0 },
        hoverIntensity: { value: hoverIntensity },
        speechActivity: { value: 0 },
        backgroundColor: { value: hexToVec3(backgroundColor) },
      },
    });
    const mesh = new Mesh(gl, { geometry, program });

    gl.clearColor(0, 0, 0, 0);
    container.appendChild(gl.canvas);

    const resize = () => {
      const pixelRatio = Math.min(window.devicePixelRatio, 2);
      renderer.setSize(container.clientWidth * pixelRatio, container.clientHeight * pixelRatio);
      gl.canvas.style.width = `${container.clientWidth}px`;
      gl.canvas.style.height = `${container.clientHeight}px`;
      program.uniforms.iResolution.value.set(
        gl.canvas.width,
        gl.canvas.height,
        gl.canvas.width / gl.canvas.height,
      );
    };

    const resizeObserver = new ResizeObserver(resize);
    resizeObserver.observe(container);
    resize();

    let targetHover = 0;
    const onMouseMove = (event: MouseEvent) => {
      const rect = container.getBoundingClientRect();
      const size = Math.min(rect.width, rect.height);
      const x = ((event.clientX - rect.left - rect.width / 2) / size) * 2;
      const y = ((event.clientY - rect.top - rect.height / 2) / size) * 2;
      targetHover = Math.hypot(x, y) < 0.8 ? 1 : 0;
    };
    const onMouseLeave = () => {
      targetHover = 0;
    };
    container.addEventListener("mousemove", onMouseMove);
    container.addEventListener("mouseleave", onMouseLeave);

    let animationFrame = 0;
    let lastFrame = 0;
    let elapsed = 0;
    let rotation = 0;
    let currentSpeechActivity = 0;
    const render = (time: number) => {
      const delta = Math.min((time - lastFrame) * 0.001, 0.1);
      lastFrame = time;
      const level = Math.min(Math.max(audioLevelRef.current, 0), 1);
      const targetSpeechActivity = modeRef.current === "speaking" ? 0.16 + level * 0.34 : 0;
      currentSpeechActivity += (targetSpeechActivity - currentSpeechActivity) * 0.12;
      const speed = modeRef.current === "speaking" ? 1.2 + level : modeRef.current === "listening" ? 0.62 : 0.34;
      elapsed += delta * speed;
      const effectiveHover = forceHoverState ? 1 : targetHover;

      program.uniforms.iTime.value = elapsed;
      program.uniforms.hue.value = hue;
      program.uniforms.hoverIntensity.value = hoverIntensity;
      program.uniforms.hover.value += (effectiveHover - program.uniforms.hover.value) * 0.1;
      program.uniforms.speechActivity.value = currentSpeechActivity;
      program.uniforms.backgroundColor.value = hexToVec3(backgroundColor);

      if (rotateOnHover && effectiveHover > 0.5) rotation += delta * 0.3;
      if (modeRef.current === "speaking") rotation += delta * level * 0.16;
      program.uniforms.rot.value = rotation;
      renderer.render({ scene: mesh });
      animationFrame = requestAnimationFrame(render);
    };
    animationFrame = requestAnimationFrame(render);

    return () => {
      cancelAnimationFrame(animationFrame);
      resizeObserver.disconnect();
      container.removeEventListener("mousemove", onMouseMove);
      container.removeEventListener("mouseleave", onMouseLeave);
      gl.canvas.remove();
      gl.getExtension("WEBGL_lose_context")?.loseContext();
    };
  }, [backgroundColor, forceHoverState, hoverIntensity, hue, rotateOnHover]);

  return <div ref={containerRef} className="orb" data-mode={mode} />;
}

function hexToVec3(color: string) {
  const value = color.startsWith("#") ? color.slice(1) : color;
  if (/^[0-9a-fA-F]{6}$/.test(value)) {
    return new Vec3(
      Number.parseInt(value.slice(0, 2), 16) / 255,
      Number.parseInt(value.slice(2, 4), 16) / 255,
      Number.parseInt(value.slice(4, 6), 16) / 255,
    );
  }
  return new Vec3(0, 0, 0);
}
