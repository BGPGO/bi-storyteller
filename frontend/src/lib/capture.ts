/**
 * Screen Capture API — captures the current browser tab as a base64 PNG.
 *
 * Uses `preferCurrentTab: true` (Chrome 107+) so the user gets
 * a streamlined permission dialog focused on the current tab.
 *
 * The user needs to click "Share" once — after that we capture a single frame.
 */
export async function captureCurrentTab(): Promise<string> {
  const constraints: DisplayMediaStreamOptions = {
    video: { displaySurface: 'browser' } as MediaTrackConstraints,
    // @ts-expect-error — preferCurrentTab is a Chrome-specific extension
    preferCurrentTab: true,
  };

  const stream = await navigator.mediaDevices.getDisplayMedia(constraints);

  return new Promise((resolve, reject) => {
    const video = document.createElement('video');
    video.srcObject = stream;

    video.onloadedmetadata = () => {
      video.play().then(() => {
        // Small delay to ensure the first frame is rendered
        setTimeout(() => {
          const canvas = document.createElement('canvas');
          canvas.width = video.videoWidth;
          canvas.height = video.videoHeight;
          canvas.getContext('2d')!.drawImage(video, 0, 0);

          stream.getTracks().forEach(t => t.stop());

          const dataUrl = canvas.toDataURL('image/png');
          resolve(dataUrl.split(',')[1]); // return only base64 part
        }, 150);
      }).catch(reject);
    };

    video.onerror = () => {
      stream.getTracks().forEach(t => t.stop());
      reject(new Error('Falha ao iniciar captura de vídeo'));
    };
  });
}
