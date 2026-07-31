// Shell nativo do Foto Organizer: sobe o backend Python embarcado (porta
// efêmera), abre a janela na URL que ele anuncia e o encerra ao fechar.
//
// Arquitetura (docs/EMPACOTAMENTO.md): o webview carrega de
// http://127.0.0.1:<porta> servido pelo próprio FastAPI. Assim o front
// (URLs relativas) descobre a porta sozinho e o guard de origem local
// passa intacto — o Tauri só cuida da janela e do ciclo de vida.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::io::{BufRead, BufReader};
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use tauri::{Manager, WebviewUrl, WebviewWindowBuilder};

/// Mantém o processo do backend para encerrá-lo quando o app fecha.
struct Backend(Mutex<Option<Child>>);

fn main() {
    tauri::Builder::default()
        .manage(Backend(Mutex::new(None)))
        .setup(|app| {
            let handle = app.handle().clone();

            // Python embarcado (resource assinado):
            // <bundle>/Resources/resources/runtime/python/bin/python3
            let py = app
                .path()
                .resource_dir()?
                .join("resources/runtime/python/bin/python3");

            // Backend em porta efêmera. Ele imprime "FOTOORG_READY <url>".
            // O catálogo fica no padrão (~/Library/Application Support/...),
            // então nenhum --data-dir é passado.
            let mut child = Command::new(&py)
                // --encerrar-com-pai: o backend se auto-encerra se este
                // processo morrer de qualquer forma (rede de segurança
                // além do SIGTERM em ExitRequested abaixo) — nunca órfão.
                .args(["-m", "fotoorganizer", "web", "--porta", "0", "--encerrar-com-pai"])
                .stdout(Stdio::piped())
                .spawn()
                .expect("falha ao iniciar o backend Python embarcado");

            let stdout = child.stdout.take().expect("backend sem stdout");
            app.state::<Backend>().0.lock().unwrap().replace(child);

            // Espera o anúncio numa thread e cria a janela quando a URL chega.
            std::thread::spawn(move || {
                for line in BufReader::new(stdout).lines().map_while(Result::ok) {
                    if let Some(url) = line.strip_prefix("FOTOORG_READY ") {
                        let url = url.trim().to_string();
                        let h = handle.clone();
                        let _ = handle.run_on_main_thread(move || {
                            let _ = WebviewWindowBuilder::new(
                                &h,
                                "main",
                                WebviewUrl::External(url.parse().expect("URL inválida")),
                            )
                            .title("Foto Organizer")
                            .inner_size(1280.0, 800.0)
                            .min_inner_size(960.0, 640.0)
                            .build();
                        });
                        break;
                    }
                }
            });

            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("erro ao construir o app Tauri")
        .run(|app, event| {
            if let tauri::RunEvent::ExitRequested { .. } = event {
                if let Some(mut child) = app.state::<Backend>().0.lock().unwrap().take() {
                    // SIGTERM (não SIGKILL) → uvicorn drena e faz o checkpoint
                    // WAL antes de sair. Sem netos: os workers são threads.
                    #[cfg(unix)]
                    unsafe {
                        libc::kill(child.id() as i32, libc::SIGTERM);
                    }
                    #[cfg(not(unix))]
                    {
                        let _ = child.kill();
                    }
                    let _ = child.wait();
                }
            }
        });
}
