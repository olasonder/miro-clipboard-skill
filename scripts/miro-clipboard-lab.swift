import AppKit
import Foundation

// A local probe for Miro's macOS clipboard representations. No network calls.
// Captures may contain private board text and identifiers. Keep them out of Git.

struct Representation: Codable {
    let type: String
    let data: Data
}

struct ClipboardItem: Codable {
    let representations: [Representation]
}

struct Capture: Codable {
    let items: [ClipboardItem]
}

func read(_ board: NSPasteboard) -> Capture {
    let items = (board.pasteboardItems ?? []).map { item in
        ClipboardItem(representations: item.types.compactMap { type in
            guard let data = item.data(forType: type) else { return nil }
            return Representation(type: type.rawValue, data: data)
        })
    }
    return Capture(items: items)
}

func write(_ capture: Capture, to board: NSPasteboard) -> Bool {
    let items = capture.items.map { source in
        let item = NSPasteboardItem()
        for representation in source.representations {
            item.setData(representation.data, forType: NSPasteboard.PasteboardType(representation.type))
        }
        return item
    }
    board.clearContents()
    return board.writeObjects(items)
}

func describe(_ capture: Capture) {
    print("items: \(capture.items.count)")
    for (index, item) in capture.items.enumerated() {
        print("item \(index + 1):")
        for representation in item.representations {
            print("  \(representation.type)  \(representation.data.count) bytes")
        }
    }
}

func usage() -> Never {
    fputs("Usage:\n  swift miro-clipboard-lab.swift inspect\n  swift miro-clipboard-lab.swift show-html\n  swift miro-clipboard-lab.swift capture /path/sample.json\n  swift miro-clipboard-lab.swift replay /path/sample.json [--drop-type TYPE | --only-type TYPE] [--strip-miro-meta] [--replace-visible OLD NEW] [--set-meta-byte OFFSET VALUE | --replace-native-text OLD NEW]\n  swift miro-clipboard-lab.swift selftest\n", stderr)
    exit(2)
}

func settingMiroMetaByte(in html: String, offset: Int, value: UInt8) -> String? {
    let startMarker = "(miro-data-v1)"
    let endMarker = "(/miro-data-v1)"
    guard let start = html.range(of: startMarker),
          let end = html.range(of: endMarker, range: start.upperBound..<html.endIndex),
          let payload = Data(base64Encoded: String(html[start.upperBound..<end.lowerBound])),
          offset >= 0, offset < payload.count else { return nil }
    var modified = payload
    modified[offset] = value
    return String(html[..<start.upperBound]) + modified.base64EncodedString() + String(html[end.lowerBound...])
}

func replacingMiroNativeText(in html: String, oldText: String, newText: String) -> String? {
    guard !oldText.isEmpty else { return nil }
    let startMarker = "(miro-data-v1)"
    let endMarker = "(/miro-data-v1)"
    guard let start = html.range(of: startMarker),
          let end = html.range(of: endMarker, range: start.upperBound..<html.endIndex),
          let payload = Data(base64Encoded: String(html[start.upperBound..<end.lowerBound])) else { return nil }
    let decoded = Data(payload.map { $0 &- 59 })
    guard var root = (try? JSONSerialization.jsonObject(with: decoded)) as? [String: Any],
          var content = root["data"] as? [String: Any],
          var objects = content["objects"] as? [[String: Any]] else { return nil }
    var replacements = 0
    for index in objects.indices {
        guard var widget = objects[index]["widgetData"] as? [String: Any],
              var fields = widget["json"] as? [String: Any],
              let text = fields["text"] as? String,
              text.contains(oldText) else { continue }
        fields["text"] = text.replacingOccurrences(of: oldText, with: newText)
        widget["json"] = fields
        objects[index]["widgetData"] = widget
        replacements += 1
    }
    guard replacements > 0 else { return nil }
    content["objects"] = objects
    root["data"] = content
    guard let rewritten = try? JSONSerialization.data(withJSONObject: root),
          let json = String(data: rewritten, encoding: .utf8) else { return nil }
    let encoded = Data(json.utf8.map { $0 &+ 59 }).base64EncodedString()
    return String(html[..<start.upperBound]) + encoded + String(html[end.lowerBound...])
}

let args = Array(CommandLine.arguments.dropFirst())
guard let command = args.first else { usage() }

switch command {
case "inspect":
    guard args.count == 1 else { usage() }
    print("pasteboard change count: \(NSPasteboard.general.changeCount)")
    describe(read(.general))

case "show-html":
    guard args.count == 1 else { usage() }
    let html = read(.general).items.first?.representations.first(where: { $0.type == NSPasteboard.PasteboardType.html.rawValue })
    guard let data = html?.data, let value = String(data: data, encoding: .utf8) else {
        fputs("No UTF-8 public.html representation found.\n", stderr)
        exit(1)
    }
    print(value)

case "capture":
    guard args.count == 2 else { usage() }
    let capture = read(.general)
    guard !capture.items.isEmpty else {
        fputs("No clipboard items visible; nothing saved.\n", stderr)
        exit(1)
    }
    let url = URL(fileURLWithPath: args[1])
    do {
        let encoded = try JSONEncoder().encode(capture)
        try encoded.write(to: url, options: [.atomic])
        try FileManager.default.setAttributes([.posixPermissions: 0o600], ofItemAtPath: url.path)
        describe(capture)
        print("saved locally: \(url.path)")
    } catch {
        fputs("Capture failed: \(error)\n", stderr)
        exit(1)
    }

case "replay":
    guard args.count >= 2 else { usage() }
    var dropType: String?
    var onlyType: String?
    var stripMiroMeta = false
    var visibleReplacement: (String, String)?
    var metaByteReplacement: (Int, UInt8)?
    var nativeTextReplacement: (String, String)?
    var index = 2
    while index < args.count {
        switch args[index] {
        case "--drop-type":
            guard index + 1 < args.count, dropType == nil else { usage() }
            dropType = args[index + 1]
            index += 2
        case "--only-type":
            guard index + 1 < args.count, onlyType == nil else { usage() }
            onlyType = args[index + 1]
            index += 2
        case "--strip-miro-meta":
            stripMiroMeta = true
            index += 1
        case "--replace-visible":
            guard index + 2 < args.count, visibleReplacement == nil else { usage() }
            visibleReplacement = (args[index + 1], args[index + 2])
            index += 3
        case "--set-meta-byte":
            guard index + 2 < args.count, metaByteReplacement == nil,
                  let offset = Int(args[index + 1]),
                  let value = UInt8(args[index + 2]) else { usage() }
            metaByteReplacement = (offset, value)
            index += 3
        case "--replace-native-text":
            guard index + 2 < args.count, nativeTextReplacement == nil else { usage() }
            nativeTextReplacement = (args[index + 1], args[index + 2])
            index += 3
        default:
            usage()
        }
    }
    guard (dropType == nil || onlyType == nil),
          !(stripMiroMeta && (metaByteReplacement != nil || nativeTextReplacement != nil)),
          !(metaByteReplacement != nil && nativeTextReplacement != nil) else { usage() }
    do {
        let data = try Data(contentsOf: URL(fileURLWithPath: args[1]))
        let source = try JSONDecoder().decode(Capture.self, from: data)
        var didReplaceVisibleText = false
        var didReplaceMetaByte = false
        var didReplaceNativeText = false
        let capture = Capture(items: source.items.map { item in
            ClipboardItem(representations: item.representations.compactMap { representation in
                if representation.type == dropType || (onlyType != nil && representation.type != onlyType) {
                    return nil
                }
                if representation.type == NSPasteboard.PasteboardType.html.rawValue,
                   let html = String(data: representation.data, encoding: .utf8) {
                    var modified = stripMiroMeta
                        ? html.replacingOccurrences(of: #" data-meta="[^"]*""#, with: "", options: .regularExpression)
                        : html
                    if let (offset, value) = metaByteReplacement,
                       let updated = settingMiroMetaByte(in: modified, offset: offset, value: value) {
                        modified = updated
                        didReplaceMetaByte = true
                    }
                    if let (oldText, newText) = nativeTextReplacement,
                       let updated = replacingMiroNativeText(in: modified, oldText: oldText, newText: newText) {
                        modified = updated
                        didReplaceNativeText = true
                    }
                    if let (oldText, newText) = visibleReplacement,
                       let end = modified.range(of: "</span>") {
                        let prefix = String(modified[..<end.upperBound])
                        let visible = String(modified[end.upperBound...])
                        if visible.contains(oldText) {
                            modified = prefix + visible.replacingOccurrences(of: oldText, with: newText)
                            didReplaceVisibleText = true
                        }
                    }
                    return Representation(type: representation.type, data: Data(modified.utf8))
                }
                return representation
            })
        })
        guard capture.items.allSatisfy({ !$0.representations.isEmpty }) else {
            fputs("No representations remain after filtering.\n", stderr)
            exit(1)
        }
        guard visibleReplacement == nil || didReplaceVisibleText else {
            fputs("Visible text to replace was not found after the Miro metadata span.\n", stderr)
            exit(1)
        }
        guard metaByteReplacement == nil || didReplaceMetaByte else {
            fputs("Miro metadata or requested byte offset was not found.\n", stderr)
            exit(1)
        }
        guard nativeTextReplacement == nil || didReplaceNativeText else {
            fputs("Native text to replace was not found in a Miro object.\n", stderr)
            exit(1)
        }
        guard write(capture, to: .general) else {
            fputs("Could not write the clipboard.\n", stderr)
            exit(1)
        }
        print("wrote \(capture.items.count) item(s) to the clipboard")
        describe(read(.general))
    } catch {
        fputs("Replay failed: \(error)\n", stderr)
        exit(1)
    }

case "selftest":
    guard args.count == 1 else { usage() }
    let nativeFixture = #"{"data":{"objects":[{"widgetData":{"json":{"text":"<p>HELLO_B</p>"}}}]}}"#
    let nativePayload = Data(nativeFixture.utf8.map { $0 &+ 59 }).base64EncodedString()
    let nativeHTML = "<span data-meta=\"(miro-data-v1)\(nativePayload)(/miro-data-v1)\"></span>"
    let rewrittenHTML = replacingMiroNativeText(in: nativeHTML, oldText: "HELLO_B", newText: "A longer idea")
    let rewrittenPayload = rewrittenHTML.flatMap { html -> Data? in
        guard let start = html.range(of: "(miro-data-v1)"),
              let end = html.range(of: "(/miro-data-v1)", range: start.upperBound..<html.endIndex) else { return nil }
        return Data(base64Encoded: String(html[start.upperBound..<end.lowerBound]))
    }
    let rewrittenJSON = rewrittenPayload.flatMap { String(data: Data($0.map { $0 &- 59 }), encoding: .utf8) }
    let rewrittenText = rewrittenJSON
        .flatMap { $0.data(using: .utf8) }
        .flatMap { try? JSONSerialization.jsonObject(with: $0) as? [String: Any] }
        .flatMap { ($0["data"] as? [String: Any])?["objects"] as? [[String: Any]] }
        .flatMap { $0.first?["widgetData"] as? [String: Any] }
        .flatMap { ($0["json"] as? [String: Any])?["text"] as? String }
    let sample = Capture(items: [ClipboardItem(representations: [
        Representation(type: NSPasteboard.PasteboardType.string.rawValue, data: Data("Test".utf8)),
        Representation(type: NSPasteboard.PasteboardType.html.rawValue, data: Data("<p>Test</p>".utf8)),
    ])])
    let encoded = try JSONEncoder().encode(sample)
    let decoded = try JSONDecoder().decode(Capture.self, from: encoded)
    guard decoded.items.count == 1,
          decoded.items[0].representations.count == 2,
          decoded.items[0].representations[0].data == Data("Test".utf8),
          decoded.items[0].representations[1].data == Data("<p>Test</p>".utf8),
          settingMiroMetaByte(in: "<span data-meta=\"(miro-data-v1)QQ==(/miro-data-v1)\"></span>", offset: 0, value: 66)?
              .contains("(miro-data-v1)Qg==(/miro-data-v1)") == true,
          rewrittenText == "<p>A longer idea</p>" else {
        fatalError("Serialization round trip mismatch")
    }
    print("selftest passed: clipboard serialization and Miro metadata rewriting")

default:
    usage()
}
