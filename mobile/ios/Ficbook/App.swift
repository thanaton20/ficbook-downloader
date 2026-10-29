import UIKit

@main
final class AppDelegate: UIResponder, UIApplicationDelegate {
    func application(
        _ application: UIApplication,
        configurationForConnecting connectingSceneSession: UISceneSession,
        options: UIScene.ConnectionOptions
    ) -> UISceneConfiguration {
        let configuration = UISceneConfiguration(name: nil, sessionRole: connectingSceneSession.role)
        configuration.delegateClass = SceneDelegate.self
        return configuration
    }
}

final class SceneDelegate: UIResponder, UIWindowSceneDelegate {
    var window: UIWindow?

    func scene(_ scene: UIScene, willConnectTo session: UISceneSession, options connectionOptions: UIScene.ConnectionOptions) {
        guard let scene = scene as? UIWindowScene else { return }
        let window = UIWindow(windowScene: scene)
        window.rootViewController = WebAppController()
        window.overrideUserInterfaceStyle = .light
        window.makeKeyAndVisible()
        self.window = window
    }
}

enum Palette {
    static let background = UIColor(red: 0xEE / 255, green: 0xF1 / 255, blue: 0xEF / 255, alpha: 1)
    static let card = UIColor(red: 0xFB / 255, green: 0xFC / 255, blue: 0xFB / 255, alpha: 1)
    static let ink = UIColor(red: 0x26 / 255, green: 0x33 / 255, blue: 0x2F / 255, alpha: 1)
    static let muted = UIColor(red: 0x69 / 255, green: 0x75 / 255, blue: 0x6F / 255, alpha: 1)
    static let line = UIColor(red: 0xD4 / 255, green: 0xDC / 255, blue: 0xD8 / 255, alpha: 1)
    static let accent = UIColor(red: 0x3F / 255, green: 0x6B / 255, blue: 0x60 / 255, alpha: 1)
}
