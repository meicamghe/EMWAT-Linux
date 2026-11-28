use std::{
    collections::{BTreeMap, BTreeSet},
    env, fs,
    path::PathBuf,
    process,
    fmt::Write as _,
};

use undelphi::DelphiBinary;

fn main() {
    if let Err(error) = run() {
        eprintln!("EMWAT undelphi probe failed: {error}");
        process::exit(1);
    }
}

fn run() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<String> = env::args().collect();
    if args.len() != 3 {
        return Err("usage: emwat-undelphi-probe <PE/BPL input> <output-directory>".into());
    }

    let input = PathBuf::from(&args[1]);
    let output_dir = PathBuf::from(&args[2]);
    fs::create_dir_all(&output_dir)?;
    let report_path = output_dir.join("undelphi-report.md");
    let seeds_path = output_dir.join("rea-method-seeds.tsv");

    let bytes = fs::read(&input)?;
    let bin = match DelphiBinary::parse(&bytes) {
        Ok(binary) => binary,
        Err(error) => {
            fs::write(
                &report_path,
                format!(
                    "# EMWAT undelphi probe\n\n- Input: `{}`\n- Size: {} bytes\n- Parse result: **not recognised**\n- Error: `{}`\n",
                    input.display(),
                    bytes.len(),
                    error
                ),
            )?;
            fs::write(&seeds_path, "# No seeds: input was not recognised by undelphi.\n")?;
            return Err(format!("undelphi did not recognise {}: {error}", input.display()).into());
        }
    };

    let mut report = String::new();
    writeln!(report, "# EMWAT Delphi PE/BPL metadata probe")?;
    writeln!(report)?;
    writeln!(report, "- Input: `{}`", input.display())?;
    writeln!(report, "- Input size: {} bytes", bytes.len())?;
    writeln!(report, "- Format: `{:?}`", bin.format())?;
    writeln!(report, "- Confidence: `{:?}`", bin.confidence())?;
    writeln!(report, "- Parsed classes: {}", bin.classes().len())?;
    writeln!(report, "- Class roots: {}", bin.classes().root_count())?;
    writeln!(report, "- External-parent classes: {}", bin.classes().external_parent_count())?;
    writeln!(report, "- Maximum class depth: {}", bin.classes().max_depth())?;
    writeln!(report, "- Form resources: {}", bin.forms().len())?;
    writeln!(report)?;

    if let Some(info) = bin.compiler() {
        writeln!(report, "## Compiler identification")?;
        writeln!(report, "- Compiler: `{:?}`", info.compiler)?;
        writeln!(report, "- Version: `{:?}`", info.version)?;
        writeln!(report, "- Product: `{}`", info.product_name().unwrap_or_else(|| "<unknown>".to_string()))?;
        writeln!(report, "- Target: `{:?}/{:?}`", info.os, info.arch)?;
        writeln!(report, "- Detection source: `{:?}`", info.source)?;
        writeln!(report, "- Raw marker: `{}`", info.raw)?;
        writeln!(report)?;
    } else {
        writeln!(report, "## Compiler identification")?;
        writeln!(report, "- No compiler build marker was identified; class-layout detection is reported separately.")?;
        writeln!(report)?;
    }

    let packages = bin.required_packages();
    writeln!(report, "## Runtime packages")?;
    if packages.is_empty() {
        writeln!(report, "- No package imports were identified.")?;
    } else {
        for package in packages {
            writeln!(report, "- `{}`", package)?;
        }
    }
    writeln!(report)?;

    let text_section = bin.ctx().sections().text;
    let text_range = text_section.map(|section| {
        let size = u64::try_from(section.size).unwrap_or(u64::MAX);
        (section.va, section.va.saturating_add(size))
    });
    if let Some((start, end)) = text_range {
        writeln!(report, "## Executable section")?;
        writeln!(report, "- .text VA range: `0x{start:08X}–0x{end:08X}`")?;
        writeln!(report)?;
    }

    let mut seed_candidates: BTreeMap<u64, BTreeSet<String>> = BTreeMap::new();
    let mut out_of_text_methods = 0usize;
    let mut published_method_count = 0usize;
    let mut extended_method_count = 0usize;
    let mut extended_field_count = 0usize;

    writeln!(report, "## Classes")?;
    for class in bin.classes().iter() {
        let parent = bin.parent_class(class).map(|p| p.name().to_string())
            .or_else(|| bin.external_parent(class).map(|p| format!("external:{}:{}", p.module(), p.name())))
            .unwrap_or_else(|| "<root-or-unresolved>".to_string());
        let unit = bin.unit_name(class).unwrap_or("<unknown>");
        writeln!(report)?;
        writeln!(
            report,
            "### {} — VMT `0x{:08X}`, instance size `0x{:X}`",
            class.name(),
            class.vmt_va(),
            class.instance_size()
        )?;
        writeln!(report, "- Unit: `{}`", unit)?;
        writeln!(report, "- Parent: `{}`", parent)?;

        let fields = bin.fields(class);
        if !fields.is_empty() {
            writeln!(report, "- Classic fields ({}):", fields.len())?;
            for field in &fields {
                let ty = bin.field_type(class, field)
                    .map(|header| header.name().to_string())
                    .unwrap_or_else(|| format!("{:?}", field.type_ref));
                writeln!(report, "  - `+0x{:X}` `{}`: `{}`", field.offset, field.name(), ty)?;
            }
        }

        let extended_fields = bin.extended_fields(class);
        extended_field_count += extended_fields.len();
        if !extended_fields.is_empty() {
            writeln!(report, "- Extended fields ({}):", extended_fields.len())?;
            for field in &extended_fields {
                let ty = bin.extended_field_type(class, field)
                    .map(|header| header.name().to_string())
                    .unwrap_or_else(|| format!("type-ref 0x{:X}", field.type_ref));
                writeln!(
                    report,
                    "  - [{:?}] `+0x{:X}` `{}`: `{}`",
                    field.visibility,
                    field.offset,
                    field.name(),
                    ty
                )?;
            }
        }

        let methods = bin.methods(class);
        published_method_count += methods.len();
        if !methods.is_empty() {
            writeln!(report, "- Published methods ({}):", methods.len())?;
            for method in &methods {
                writeln!(report, "  - `0x{:08X}` `{}`", method.code_va, method.name())?;
                add_seed(
                    &mut seed_candidates,
                    method.code_va,
                    &format!("{}.{}", class.name(), method.name()),
                    text_range,
                    &mut out_of_text_methods,
                );
            }
        }

        let extended_methods = bin.extended_methods(class);
        extended_method_count += extended_methods.len();
        if !extended_methods.is_empty() {
            writeln!(report, "- Extended methods ({}):", extended_methods.len())?;
            for method in &extended_methods {
                let info = method.info();
                writeln!(
                    report,
                    "  - `0x{:08X}` `{}` flags=`0x{:04X}` vmt-index=`{}` abstract=`{}`",
                    method.code_va,
                    method.name(),
                    method.flags,
                    method.vmt_index,
                    info.is_abstract()
                )?;
                if !info.is_abstract() {
                    add_seed(
                        &mut seed_candidates,
                        method.code_va,
                        &format!("{}.{}", class.name(), method.name()),
                        text_range,
                        &mut out_of_text_methods,
                    );
                }
            }
        }

        let virtual_methods = bin.virtual_methods(class);
        if !virtual_methods.is_empty() {
            writeln!(report, "- Virtual slots ({}):", virtual_methods.len())?;
            for slot in virtual_methods {
                writeln!(
                    report,
                    "  - slot {} at `0x{:08X}` → `0x{:08X}`",
                    slot.slot,
                    slot.slot_va,
                    slot.code_va
                )?;
            }
        }
    }

    let mut seeds = String::from("# REA Ghidra seed file: address<TAB>kind<TAB>name\n");
    let mut ambiguous = Vec::new();
    let mut emitted = 0usize;
    for (address, names) in &seed_candidates {
        if names.len() != 1 {
            ambiguous.push((*address, names.iter().cloned().collect::<Vec<_>>()));
            continue;
        }
        if let Some(name) = names.iter().next() {
            writeln!(seeds, "0x{address:08X}\tfunction\t{name}")?;
            emitted += 1;
        }
    }

    writeln!(report)?;
    writeln!(report, "## Seed and parser summary")?;
    writeln!(report, "- Published methods decoded: {published_method_count}")?;
    writeln!(report, "- Extended methods decoded: {extended_method_count}")?;
    writeln!(report, "- Extended fields decoded: {extended_field_count}")?;
    writeln!(report, "- Unique method addresses considered: {}", seed_candidates.len())?;
    writeln!(report, "- REA function seeds emitted (unique names, .text only): {emitted}")?;
    writeln!(report, "- Methods rejected outside .text: {out_of_text_methods}")?;
    writeln!(report, "- Ambiguous code addresses omitted: {}", ambiguous.len())?;
    for (address, names) in ambiguous {
        writeln!(report, "  - `0x{address:08X}`: {}", names.join(" | "))?;
    }
    writeln!(report)?;
    writeln!(report, "## Evidence limits")?;
    writeln!(report, "- This is static parsing only; no Windows execution, Word automation, scanner, printer, or Almas round-trip is tested.")?;
    writeln!(report, "- A parsed field/method is a binary metadata fact, not proof that its behavior is understood.")?;
    writeln!(report, "- REA seeds are emitted only for uniquely named method addresses inside the PE .text range; ambiguous and out-of-range addresses are excluded.")?;

    fs::write(&report_path, report)?;
    fs::write(&seeds_path, seeds)?;
    println!(
        "Parsed {} classes; published methods {}; extended methods {}; extended fields {}; emitted {} REA seeds.",
        bin.classes().len(),
        published_method_count,
        extended_method_count,
        extended_field_count,
        emitted
    );
    Ok(())
}

fn add_seed(
    candidates: &mut BTreeMap<u64, BTreeSet<String>>,
    address: u64,
    name: &str,
    text_range: Option<(u64, u64)>,
    out_of_text: &mut usize,
) {
    let in_text = text_range.is_some_and(|(start, end)| address >= start && address < end);
    if !in_text || name.contains("<non-ascii>") {
        *out_of_text += 1;
        return;
    }
    candidates.entry(address).or_default().insert(name.to_string());
}
