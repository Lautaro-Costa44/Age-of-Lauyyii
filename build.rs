//! Incrusta el ícono en el .exe de Windows (lo que se ve en el Explorador,
//! la barra de tareas y el acceso directo).

fn main() {
    println!("cargo:rerun-if-changed=assets/icono.ico");
    if std::env::var("CARGO_CFG_TARGET_OS").as_deref() == Ok("windows") {
        let mut res = winresource::WindowsResource::new();
        res.set_icon("assets/icono.ico");
        res.set("FileDescription", "Age of Lauyyii - guía de Age of Empires II");
        res.set("ProductName", "Age of Lauyyii");
        if let Err(e) = res.compile() {
            println!("cargo:warning=No pude incrustar el ícono del .exe: {e}");
        }
    }
}
