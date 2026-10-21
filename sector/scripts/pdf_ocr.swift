import Foundation
import Vision
import ImageIO
let input = URL(fileURLWithPath: CommandLine.arguments[1])
let request = VNRecognizeTextRequest()
request.recognitionLevel = .accurate
request.usesLanguageCorrection = false
let supported = try request.supportedRecognitionLanguages()
request.recognitionLanguages = ["tr-TR", "en-US"].filter { supported.contains($0) }
try VNImageRequestHandler(url: input, options: [:]).perform([request])
let result = (request.results ?? []).compactMap { observation -> [String: Any]? in
 guard let text = observation.topCandidates(1).first else { return nil }
 let b = observation.boundingBox
 return ["text": text.string, "confidence": text.confidence, "x": b.minX, "y": 1-b.maxY, "width": b.width, "height": b.height]
}
let data = try JSONSerialization.data(withJSONObject: result, options: [.sortedKeys])
FileHandle.standardOutput.write(data)
